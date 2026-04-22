# Procedura zarządzania magazynem — Firma ABC

**Dokument:** LOG-001  
**Wersja:** 2.5  
**Data aktualizacji:** 2023-09-01  
**Właściciel:** Kierownik Logistyki  

---

## 1. Struktura magazynu

Firma ABC posiada cztery strefy magazynowe w hali głównej (budynek B):

| Strefa | Oznaczenie | Przeznaczenie |
|---|---|---|
| M-0 | Kwarantanna | Materiały oczekujące na kontrolę QA |
| M-1 | Surowce | Zatwierdzone surowce i komponenty |
| M-2 | Półfabrykaty | Produkcja w toku, między operacjami |
| M-3 | Wyroby gotowe | Produkty gotowe do wysyłki |
| M-4 | Zwroty | Reklamacje od klientów, materiał do oceny |

Poruszanie się między strefami wymaga aktualizacji statusu w systemie ERP (moduł Gospodarka Magazynowa — WM).

---

## 2. Przyjęcie materiałów (GR — Goods Receipt)

### 2.1 Przyjęcie od dostawcy

1. Kierowca dostarcza dokumenty przewozowe (WZ, CMR) do biura bramki wjazdowej
2. Pracownik magazynu weryfikuje zgodność dostawy z PO w systemie ERP:
   - Numer PO na dokumentach = PO w ERP
   - Ilość na WZ ≤ ilość zamówiona
   - Dostawca = dostawca z PO
3. Materiał rozładowywany i umieszczany w strefie **M-0 (Kwarantanna)**
4. Pracownik skanuje kody kreskowe lub etykiety GS1 i potwierdza GR w ERP
5. System automatycznie generuje etykietę wewnętrzną z numerem partii (batch number)
6. Dokumenty dostarczone do Działu Zakupów (oryginał WZ) i QA (kopia do kontroli)

### 2.2 Przyjęcie z produkcji (wyroby gotowe)

1. Mistrz Produkcji inicjuje GR w systemie MES po zakończeniu zlecenia
2. QA przeprowadza kontrolę końcową (FQC) i zmienia status w ERP na "GOTOWE DO WYSYŁKI"
3. Pracownik magazynu przenosi wyrób do strefy M-3 i potwierdza lokalizację w ERP
4. Wyroby układane wg zasady FEFO (First Expired First Out) — data produkcji widoczna na etykiecie

---

## 3. Wydanie materiałów (GI — Goods Issue)

### 3.1 Wydanie na produkcję

1. Planista Produkcji generuje listę kompletacyjną (Pick List) w ERP dla każdego ZP
2. Magazynier kompletuje materiały wg listy — skanuje każdą pozycję
3. Przekazanie na linię produkcyjną — magazynier i Mistrz Produkcji potwierdzają odbiór w MES
4. Zużycie automatycznie księgowane w ERP po potwierdzeniu GI

### 3.2 Wydanie do wysyłki (do klienta)

1. Podstawą wydania jest zatwierdzone zamówienie klienta (SO — Sales Order) w ERP
2. Magazynier wystawia dokument WZ w systemie i drukuje etykiety wysyłkowe
3. Wyroby kompletowane z M-3, weryfikowane z zamówieniem
4. Załadunek i przekazanie dokumentów kierowcy
5. ERP automatycznie wystawia fakturę (lub faktura wystawiana przez Dział Sprzedaży)

---

## 4. Inwentaryzacja

### 4.1 Inwentaryzacja roczna

- Przeprowadzana raz w roku w grudniu (zazwyczaj w tygodniu poprzedzającym Święta)
- Magazyn zamknięty dla ruchu materiałowego w dniu inwentaryzacji
- Komisja inwentaryzacyjna: Kierownik Logistyki + Kontroler Finansowy + przedstawiciel działu
- Różnice inwentaryzacyjne (niedobory >500 PLN) wymagają wyjaśnienia i akceptacji CFO

### 4.2 Inwentaryzacja ciągła (Cycle Count)

- Co tydzień, losowy wybór 50 pozycji w ERP
- Magazynier przelicza fizycznie i porównuje ze stanem ERP
- Różnice powyżej 2% wartości → korekta i analiza przyczyn przez Kierownika Logistyki

---

## 5. FIFO / FEFO

Firma ABC stosuje zasadę **FEFO** (First Expired First Out) dla materiałów z datą ważności oraz **FIFO** (First In First Out) dla pozostałych. Etykiety wewnętrzne zawierają datę przyjęcia i datę ważności (jeśli dotyczy). Wydawanie z naruszeniem FEFO/FIFO jest niedozwolone bez zgody QA.

---

## 6. Kontakt

- **Kierownik Logistyki:** logistyka@firma-abc.pl, wew. 350
- **Dyspozytornia magazynowa:** wew. 360
- **Bramka wjazdowa:** wew. 370 (24/7)
