# Procedura kontroli jakości produkcji — Firma ABC

**Dokument:** PROD-001  
**Wersja:** 4.0  
**Data aktualizacji:** 2024-01-10  
**Właściciel:** Dział Jakości (QA)  

---

## 1. Cel i zakres

Procedura obejmuje kontrolę jakości na wszystkich etapach produkcji w zakładzie Firma ABC w Poznaniu. Dotyczy linii produkcyjnych L1–L6 i ma zastosowanie do wszystkich wyrobów gotowych oraz półfabrykatów.

---

## 2. Etapy kontroli jakości

### 2.1 Kontrola wejściowa surowców (IQC — Incoming Quality Control)

**Cel:** Weryfikacja jakości surowców i komponentów przed dopuszczeniem do produkcji.

**Procedura:**
1. Każda dostawa surowców jest zatrzymana w strefie kwarantanny (magazyn M-0) do czasu kontroli.
2. Inspektor QA pobiera próbki wg planu pobierania próbek (dokument QA-SP-001).
3. Badania laboratoryjne muszą zostać zakończone w ciągu **24 godzin** od dostawy.
4. Wynik kontroli wprowadzany jest do systemu ERP (moduł QM).
5. Dopiero po statusie "ZWOLNIONO" w ERP magazyn może przekazać materiał na produkcję.

**W przypadku niezgodności:**
- Materiał pozostaje w kwarantannie z etykietą czerwoną "NIEZGODNE"
- Inspektor QA wystawia raport niezgodności NCR (Non-Conformance Report) w systemie ERP
- Decyzja: zwrot do dostawcy / przerób / złomowanie — zatwierdza Kierownik QA

### 2.2 Kontrola w procesie (IPQC — In-Process Quality Control)

Kontrolerzy jakości przeprowadzają kontrole na każdej linii produkcyjnej zgodnie z Planem Kontroli (CP — Control Plan, dokument QA-CP-00X dla danej linii).

**Częstotliwość kontroli:**
- Linie L1–L3 (wyroby klasy A): co 2 godziny
- Linie L4–L6 (wyroby klasy B): co 4 godziny
- Przy starcie każdej zmiany: First Article Inspection (FAI)

**Parametry kontrolowane:**
- Wymiary geometryczne (zgodnie z rysunkiem technicznym)
- Właściwości fizyczne (twardość, wytrzymałość)
- Wygląd zewnętrzny (wady powierzchni wg katalogu wad QA-WZ-001)
- Oznakowanie i etykietowanie

**Wyniki kontroli** wpisywane są do systemu MES (Manufacturing Execution System) w czasie rzeczywistym. Automatyczny alert SPC (Statistical Process Control) generuje powiadomienie przy przekroczeniu granic kontrolnych.

### 2.3 Kontrola końcowa wyrobu gotowego (FQC — Final Quality Control)

- 100% kontrola wizualna przez operatora na końcu linii
- Wyrywkowa kontrola szczegółowa przez inspektora QA (poziom AQL 1.5 wg normy ISO 2859-1)
- Wystawienie Certyfikatu Zgodności (CoC) dla każdej partii
- Nadanie statusu "GOTOWE DO WYSYŁKI" w ERP

---

## 3. Niezgodności i działania korygujące (CAR)

### 3.1 Klasyfikacja niezgodności

| Klasa | Opis | Czas reakcji |
|---|---|---|
| Krytyczna (Critical) | Zagrożenie bezpieczeństwa lub funkcjonalności | Natychmiastowe zatrzymanie linii |
| Poważna (Major) | Wyrób niespełniający wymagań klienta | 4 godziny |
| Drobna (Minor) | Odchylenie niezagrażające funkcjonalności | 24 godziny |

### 3.2 Proces CAR (Corrective Action Request)

1. Inspektor QA wystawia NCR w systemie ERP
2. Kierownik Produkcji otrzymuje powiadomienie i wyznacza odpowiedzialnego
3. Analiza przyczyn źródłowych metodą 5Why lub Fishbone (w ciągu 48h)
4. Wdrożenie działania korygującego
5. Weryfikacja skuteczności działania przez QA (po 30 dniach)
6. Zamknięcie NCR w systemie

---

## 4. Dokumenty powiązane

- QA-SP-001 — Plan pobierania próbek
- QA-CP-001 do QA-CP-006 — Plany Kontroli dla linii L1–L6
- QA-WZ-001 — Katalog wad wizualnych
- PROD-005 — Procedura zarządzania niezgodnościami

---

## 5. Kontakt

- **Kierownik QA:** qa.manager@firma-abc.pl, wew. 410
- **Laboratorium:** laboratorium@firma-abc.pl, wew. 420
