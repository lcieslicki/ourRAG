# ourRAG

Repozytorium dokumentacji i danych przykladowych dla wewnetrznego projektu typu RAG.

## Struktura

- `data/firma_ABC/` - dokumenty zrodlowe Markdown pogrupowane domenowo (HR, finanse, IT itp.)
- `docs/` - zasoby pomocnicze (np. `overview.png`)
- `backend/` - szkielet backendu Python/FastAPI
- `frontend/` - szkielet frontendu React
- `infra/` - lokalna infrastruktura Docker Compose
- `tests/` - miejsce na testy end-to-end i scenariusze przekrojowe
- `CLAUDE.md`, `AGENTS.md` - wskazowki dla agentow AI

## Jak uzywac

Na ten moment repozytorium zawiera dane, dokumentacje i poczatkowy szkielet aplikacji, bez zaimplementowanej logiki biznesowej RAG.

Przydatne komendy do szybkiej weryfikacji zawartosci:

```sh
find data -name '*.md'
find docs -maxdepth 1 -type f
```

Lokalna infrastruktura:

```sh
make infra-up
make infra-logs
make infra-down
```

## Konwencja nazw dokumentow

Dla plikow w `data/firma_ABC/` uzywaj lowercase snake_case z prefiksem domeny, np.:

- `hr_praca_zdalna.md`
- `finanse_planowanie_budzetu.md`
- `it_polityka_bezpieczenstwa.md`

## Uwagi

- Zachowuj zmiany male i celowane.
- Nie zmieniaj nazw istniejacych plikow bez wyraznej potrzeby.
