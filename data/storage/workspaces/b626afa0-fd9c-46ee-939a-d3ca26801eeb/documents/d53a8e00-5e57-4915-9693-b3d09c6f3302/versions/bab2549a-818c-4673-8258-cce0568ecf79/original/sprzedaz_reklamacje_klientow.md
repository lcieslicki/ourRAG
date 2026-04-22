# Procedura reklamacji od klientów — Firma ABC

**Dokument:** SPRZED-001  
**Wersja:** 1.9  
**Data aktualizacji:** 2024-01-08  
**Właściciel:** Dział Sprzedaży / QA  

---

## 1. Cel i zakres

Procedura określa sposób przyjmowania, rejestrowania, rozpatrywania i zamykania reklamacji składanych przez klientów zewnętrznych Firmy ABC.

---

## 2. Kanały przyjmowania reklamacji

| Kanał | Adres / dane | Odpowiedzialny |
|---|---|---|
| E-mail | reklamacje@firma-abc.pl | Dział Sprzedaży |
| Portal klienta | klient.firma-abc.pl/reklamacje | Dział Sprzedaży |
| Telefon | +48 61 555 0200 | Dział Sprzedaży |
| Pismo | Firma ABC Sp. z o.o., ul. Przemysłowa 5, 60-001 Poznań | Sekretariat → Sprzedaż |

---

## 3. Klasyfikacja reklamacji

| Typ | Opis | Czas odpowiedzi klientowi |
|---|---|---|
| Jakościowa | Wada produktu, niezgodność z spec. | 5 dni roboczych |
| Ilościowa | Błędna ilość w dostawie | 3 dni robocze |
| Dostawcza | Opóźnienie, uszkodzenie w transporcie | 3 dni robocze |
| Fakturowa | Błąd na fakturze | 2 dni robocze |

---

## 4. Procedura krok po kroku

### Krok 1 — Rejestracja (Dział Sprzedaży, dzień 0)

1. Opiekun klienta rejestruje reklamację w systemie CRM (crm.firma-abc.pl) w ciągu **4 godzin** od wpłynięcia
2. Nadaje numer reklamacji (format: RKL-RRRR-NNNNN)
3. Wysyła do klienta automatyczne potwierdzenie przyjęcia z numerem RKL i deklarowanym czasem odpowiedzi
4. Przekazuje sprawę do QA (dla reklamacji jakościowych) lub do właściwego działu

### Krok 2 — Ocena wstępna (QA lub dział właściwy, dzień 1–2)

Dla reklamacji jakościowych QA:
- Analizuje dokumentację (protokoły kontroli, certyfikaty partii)
- Może zażądać przesłania wadliwej próbki od klienta (RMA — Return Merchandise Authorization)
- Ocenia: uznana / nieuznana / wymaga dodatkowych badań

### Krok 3 — Decyzja i propozycja rozwiązania (dzień 3–5)

Możliwe decyzje:

| Decyzja | Działanie |
|---|---|
| Reklamacja uznana | Wymiana towaru / korekta faktury / rabat — wg uzgodnienia z klientem |
| Reklamacja częściowo uznana | Częściowa korekta — uzasadnienie pisemne |
| Reklamacja nieuznana | Pismo z uzasadnieniem do klienta (wymaga akceptacji Dyrektora Sprzedaży) |

Decyzja komunikowana klientowi pisemnie (e-mail) z numerem RKL.

### Krok 4 — Realizacja decyzji

- Wymiana towaru: zlecenie produkcyjne ZP-E (ekspresowe) lub wydanie z M-3 — koordynuje Dział Sprzedaży z Logistyką
- Korekta faktury: wystawiana przez Dział Finansowy w ciągu 3 dni od decyzji
- Zwrot materiału od klienta: materiał trafia do strefy M-4 (Zwroty) w magazynie

### Krok 5 — Analiza przyczynowa i działania korygujące

Dla reklamacji uznanych QA przeprowadza analizę 8D (formularz QA-F-030):
1. D1 — Powołanie zespołu
2. D2 — Opis problemu
3. D3 — Działania tymczasowe (containment)
4. D4 — Analiza przyczyn źródłowych (5Why / Fishbone)
5. D5–D7 — Działania korygujące i zapobiegawcze
6. D8 — Zamknięcie i gratulacje dla zespołu

Raport 8D wysyłany do klienta (jeśli tego wymaga) i archiwizowany w systemie QA.

### Krok 6 — Zamknięcie reklamacji

- Opiekun klienta zamyka RKL w CRM po potwierdzeniu realizacji decyzji
- Klient otrzymuje ankietę satysfakcji z obsługi reklamacji (NPS)
- Dane zasilają raport miesięczny reklamacji (Dyrektor Sprzedaży + QA)

---

## 5. Raportowanie

Co miesiąc Dział QA przygotowuje raport reklamacji zawierający:
- Liczbę i wartość reklamacji uznanych / nieuznanych
- Wskaźnik PPM (Parts Per Million) wg klienta
- Top 5 przyczyn reklamacji
- Status otwartych działań korygujących (CAR)

Raport prezentowany na miesięcznym spotkaniu zarządu.

---

## 6. Kontakt

- **Obsługa reklamacji:** reklamacje@firma-abc.pl
- **Kierownik Sprzedaży:** sprzedaz@firma-abc.pl, wew. 220
- **QA (reklamacje):** qa.reklamacje@firma-abc.pl, wew. 415
