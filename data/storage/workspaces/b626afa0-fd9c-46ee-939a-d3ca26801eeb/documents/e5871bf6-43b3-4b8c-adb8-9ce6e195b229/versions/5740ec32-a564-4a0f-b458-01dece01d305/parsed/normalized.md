# Procedura zarządzania zleceniami produkcyjnymi — Firma ABC

**Dokument:** PROD-002
**Wersja:** 2.3
**Data aktualizacji:** 2023-11-20
**Właściciel:** Dział Planowania Produkcji

---

## 1. Cel dokumentu

Procedura określa zasady tworzenia, uruchamiania, realizacji i zamykania zleceń produkcyjnych (ZP) w systemie ERP (IFS) w Firmie ABC.

---

## 2. Rodzaje zleceń produkcyjnych

| Typ | Opis | Priorytet |
|---|---|---|
| ZP-S | Zlecenie standardowe (plan) | Normalny |
| ZP-E | Zlecenie ekspresowe (na żądanie klienta) | Wysoki |
| ZP-R | Zlecenie na remont / naprawę | Normalny |
| ZP-P | Zlecenie prototypowe | Specjalny |

---

## 3. Proces tworzenia zlecenia produkcyjnego

### 3.1 Źródła zleceń

Zlecenia produkcyjne są generowane przez:
- **MRP** (Material Requirements Planning) — automatycznie z systemu ERP na podstawie zamówień klientów i prognozy popytu
- **Ręcznie** przez Planistę Produkcji — w przypadkach nieobsłużonych przez MRP

### 3.2 Warunki otwarcia zlecenia

Przed uruchomieniem ZP planista weryfikuje:
1. Dostępność surowców i komponentów (status "ZWOLNIONO" w magazynie)
2. Dostępność maszyn (brak planowanych przeglądów, awarii)
3. Dostępność pracowników (plan zmianowy)
4. Aktualna dokumentacja technologiczna (rysunki, karty technologiczne) zatwierdzona w systemie PDM

Jeśli którykolwiek warunek nie jest spełniony — ZP pozostaje w statusie "WSTRZYMANE" z adnotacją przyczyny.

### 3.3 Uruchomienie zlecenia

1. Planista zmienia status ZP na "ZWOLNIONE" w ERP
2. System automatycznie drukuje kartę zlecenia produkcyjnego i etykiety na materiał
3. Magazyn kompletuje materiały i dostarcza na linię produkcyjną w ciągu **2 godzin**
4. Mistrz Produkcji potwierdza odbiór materiałów w systemie MES

---

## 4. Realizacja zlecenia

### 4.1 Raportowanie produkcji

Operatorzy raportują postęp produkcji w systemie MES po każdej operacji:
- Ilość sztuk zgodnych
- Ilość sztuk niezgodnych (z podaniem kodu przyczyny)
- Czas operacji (automatycznie z czytnika kart)
- Zużycie materiałów (potwierdzenie lub korekta)

### 4.2 Odchylenia od planu

Jeśli rzeczywisty czas produkcji przekracza planowany o więcej niż **15%**, Mistrz Produkcji jest zobowiązany do:
1. Odnotowania przyczyny w systemie MES (lista rozwijana: awaria, brak materiału, problem jakościowy, inne)
2. Powiadomienia Planisty Produkcji o opóźnieniu
3. Oceny wpływu na harmonogram kolejnych zleceń

---

## 5. Zamknięcie zlecenia

### 5.1 Warunki zamknięcia

ZP może zostać zamknięte gdy:
- Wyprodukowano min. 98% planowanej ilości (lub 100% po uzgodnieniu z klientem)
- QA nadał status "GOTOWE DO WYSYŁKI" dla partii
- Wszystkie operacje zostały zaraportowane w MES
- Materiały zostały rozliczone (zużycie zgodne z BOM ±5%)

### 5.2 Procedura zamknięcia

1. Mistrz Produkcji inicjuje zamknięcie w MES
2. System ERP automatycznie:
   - Rozlicza materiały (aktualizuje stany magazynowe)
   - Kalkuluje rzeczywisty koszt produkcji
   - Generuje raport odchyleń (plan vs. realizacja)
3. Planista weryfikuje raport odchyleń — jeśli koszt odchyla się o >10%, wymagana akceptacja Kontrolera Finansowego

---

## 6. Kontakt

- **Planowanie Produkcji:** planowanie@firma-abc.pl, wew. 430
- **Mistrz Produkcji (zmiana dzienna):** wew. 440
- **Helpdesk ERP:** erp-support@firma-abc.pl, wew. 310
