import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/App";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("MVP chat UI", () => {
  it("keeps the active workspace explicit and loads workspace conversations", async () => {
    const fetchMock = mockApi({
      conversations: [
        conversation({
          id: "conv-1",
          workspace_id: "workspace-1",
          title: "Vacation policy",
        }),
      ],
      documents: [],
    });

    render(<App />);
    await chooseWorkspace("user-1", "workspace-1");

    expect(await screen.findByRole("button", { name: /Vacation policy active/i })).toBeInTheDocument();
    expect(screen.getByText("Workspace").nextElementSibling).toHaveTextContent("workspace-1");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/conversations?workspace_id=workspace-1"),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-User-Id": "user-1" }),
      }),
    );
  });

  it("loads a conversation and renders assistant answers", async () => {
    mockApi({
      conversations: [conversation({ id: "conv-1", workspace_id: "workspace-1", title: "Benefits" })],
      documents: [],
      conversationDetail: {
        ...conversation({ id: "conv-1", workspace_id: "workspace-1", title: "Benefits" }),
        summary: null,
        messages: [
          message({ id: "msg-1", conversation_id: "conv-1", workspace_id: "workspace-1", role: "user", content: "What is covered?" }),
          message({
            id: "msg-2",
            conversation_id: "conv-1",
            workspace_id: "workspace-1",
            role: "assistant",
            content: "Medical coverage is described in the benefits handbook.",
          }),
        ],
      },
    });

    render(<App />);
    await chooseWorkspace("user-1", "workspace-1");
    await userEvent.click(await screen.findByRole("button", { name: /Benefits active/i }));

    expect(await screen.findByText("What is covered?")).toBeInTheDocument();
    expect(screen.getByText("Medical coverage is described in the benefits handbook.")).toBeInTheDocument();
  });

  it("renders answer sources without exposing internal version or chunk identifiers", async () => {
    mockApi({
      conversations: [conversation({ id: "conv-1", workspace_id: "workspace-1", title: "HR" })],
      documents: [],
      conversationDetail: {
        ...conversation({ id: "conv-1", workspace_id: "workspace-1", title: "HR" }),
        summary: null,
        messages: [
          message({
            id: "msg-2",
            conversation_id: "conv-1",
            workspace_id: "workspace-1",
            role: "assistant",
            content: "Vacation requests go through HR.",
            response_metadata: {
              sources: [
                {
                  document_id: "doc-1",
                  document_title: "Employee Handbook",
                  document_version_id: "version-secret",
                  chunk_id: "chunk-secret",
                  section_path: "HR > Vacation",
                  snippet: "Vacation requests must be submitted in the HR system.",
                  score: 0.91,
                  category: "HR",
                },
              ],
            },
          }),
        ],
      },
    });

    render(<App />);
    await chooseWorkspace("user-1", "workspace-1");
    await userEvent.click(await screen.findByRole("button", { name: /HR active/i }));

    const sources = screen.getByLabelText("Latest answer sources");
    expect(await within(sources).findByText("Employee Handbook")).toBeInTheDocument();
    expect(within(sources).getByText("HR > Vacation")).toBeInTheDocument();
    expect(within(sources).getByText("Vacation requests must be submitted in the HR system.")).toBeInTheDocument();
    expect(sources).not.toHaveTextContent("version-secret");
    expect(sources).not.toHaveTextContent("chunk-secret");
  });

  it("sends category and selected-document scopes with chat requests", async () => {
    const fetchMock = mockApi({
      conversations: [conversation({ id: "conv-1", workspace_id: "workspace-1", title: "HR" })],
      documents: [
        documentItem({ id: "doc-1", title: "Employee Handbook", category: "HR" }),
        documentItem({ id: "doc-2", title: "IT Guide", category: "IT" }),
      ],
      chatResponse: () => chatResponse("conv-1", "Scope acknowledged."),
    });

    render(<App />);
    await chooseWorkspace("user-1", "workspace-1");
    await userEvent.click(await screen.findByLabelText("Category"));
    await userEvent.selectOptions(screen.getByLabelText("Category", { selector: "select" }), "HR");
    await sendChatMessage("How do vacations work?");

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/chat"),
        expect.objectContaining({
          body: expect.stringContaining('"category":"HR"'),
        }),
      );
    });

    await userEvent.click(screen.getByLabelText("Selected documents"));
    await userEvent.click(screen.getByLabelText(/Employee Handbook/i));
    await sendChatMessage("Use only the handbook.");

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/chat"),
        expect.objectContaining({
          body: expect.stringContaining('"document_ids":["doc-1"]'),
        }),
      );
    });
  });

  it("shows backend errors from conversation loading", async () => {
    mockApi({
      conversationsStatus: 403,
      conversations: { detail: { code: "workspace_access_denied", message: "Access denied." } },
      documents: [],
    });

    render(<App />);
    await chooseWorkspace("user-1", "workspace-1");

    expect(await screen.findByText(/API request failed: 403/i)).toBeInTheDocument();
    expect(screen.getByText(/workspace_access_denied/i)).toBeInTheDocument();
  });
});

async function chooseWorkspace(userId: string, workspaceId: string) {
  await userEvent.type(screen.getByLabelText("User ID"), userId);
  await userEvent.type(screen.getByLabelText("Workspace ID"), workspaceId);
}

async function sendChatMessage(text: string) {
  await userEvent.type(screen.getByPlaceholderText("Ask a question..."), text);
  await userEvent.click(screen.getByRole("button", { name: "Send" }));
}

function mockApi(options: {
  conversations: unknown;
  conversationsStatus?: number;
  documents: unknown;
  conversationDetail?: unknown;
  chatResponse?: unknown | (() => unknown);
}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);

    if (url.includes("/api/conversations?")) {
      return jsonResponse(options.conversations, options.conversationsStatus ?? 200);
    }

    if (url.endsWith("/api/conversations") && init?.method === "POST") {
      return jsonResponse(conversation({ id: "conv-1", workspace_id: "workspace-1", title: "New chat" }), 201);
    }

    if (url.includes("/api/conversations/")) {
      return jsonResponse(options.conversationDetail ?? { ...conversation({ id: "conv-1" }), messages: [], summary: null });
    }

    if (url.includes("/api/documents?")) {
      return jsonResponse(options.documents);
    }

    if (url.endsWith("/api/chat")) {
      const body =
        typeof options.chatResponse === "function"
          ? options.chatResponse()
          : (options.chatResponse ?? chatResponse("conv-1", "Backend answer."));
      return jsonResponse(body);
    }

    return jsonResponse({ detail: { code: "not_found", message: url } }, 404);
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function conversation(overrides: Partial<Record<"id" | "workspace_id" | "title", string>> = {}) {
  return {
    id: overrides.id ?? "conv-1",
    workspace_id: overrides.workspace_id ?? "workspace-1",
    user_id: "user-1",
    title: overrides.title ?? "Conversation",
    status: "active",
    selected_scope: null,
    created_at: "2026-04-17T08:00:00Z",
    updated_at: "2026-04-17T08:00:00Z",
  };
}

function message(overrides: {
  id: string;
  conversation_id: string;
  workspace_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  response_metadata?: Record<string, unknown> | null;
}) {
  return {
    id: overrides.id,
    conversation_id: overrides.conversation_id,
    workspace_id: overrides.workspace_id,
    user_id: overrides.role === "user" ? "user-1" : null,
    role: overrides.role,
    content: overrides.content,
    response_metadata: overrides.response_metadata ?? null,
    created_at: "2026-04-17T08:00:00Z",
  };
}

function documentItem(overrides: { id: string; title: string; category: string }) {
  return {
    id: overrides.id,
    workspace_id: "workspace-1",
    title: overrides.title,
    slug: overrides.title.toLowerCase().replaceAll(" ", "-"),
    category: overrides.category,
    tags: [],
    status: "active",
    active_version_id: "version-1",
    latest_processing_status: "ready",
    version_count: 1,
  };
}

function chatResponse(conversationId: string, answer: string) {
  return {
    conversation_id: conversationId,
    user_message: message({
      id: `user-${crypto.randomUUID()}`,
      conversation_id: conversationId,
      workspace_id: "workspace-1",
      role: "user",
      content: "Question",
    }),
    assistant_message: {
      id: `assistant-${crypto.randomUUID()}`,
      role: "assistant",
      content: answer,
      sources: [],
    },
    usage: {},
  };
}
