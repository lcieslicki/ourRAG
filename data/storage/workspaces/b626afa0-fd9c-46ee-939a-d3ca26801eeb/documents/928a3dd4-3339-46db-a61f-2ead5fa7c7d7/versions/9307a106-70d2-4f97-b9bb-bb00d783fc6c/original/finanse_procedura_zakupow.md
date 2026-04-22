# Procedura zakupów i zamówień — Firma ABC

**Dokument:** FIN-001  
**Wersja:** 2.0  
**Data aktualizacji:** 2023-12-01  
**Właściciel:** Dział Zakupów  

---

## 1. Cel i zakres

Procedura reguluje proces zatwierdzania i realizacji zakupów towarów i usług dla wszystkich działów Firmy ABC. Celem jest zapewnienie kontroli kosztów, zgodności z budżetem i transparentności procesu zakupowego.

---

## 2. Progi autoryzacji zakupów

| Wartość netto | Wymagana autoryzacja |
|---|---|
| Do 500 PLN | Kierownik Działu (samodzielnie) |
| 501 – 5 000 PLN | Kierownik Działu + Dział Zakupów |
| 5 001 – 50 000 PLN | Dyrektor Działu + Kontroler Finansowy |
| 50 001 – 200 000 PLN | Dyrektor Generalny + CFO |
| Powyżej 200 000 PLN | Zarząd (uchwała) |

Wartości dotyczą pojedynczego zamówienia. Dzielenie zamówień w celu obejścia progów autoryzacji jest niedozwolone i stanowi naruszenie polityki compliance.

---

## 3. Procedura zakupu

### 3.1 Inicjowanie zapotrzebowania

1. Pracownik zgłasza zapotrzebowanie w systemie ERP (moduł Zakupy → Nowe Zapotrzebowanie)
2. Wypełnia formularz: opis przedmiotu, ilość, szacunkowa cena, uzasadnienie biznesowe, centrum kosztów
3. System automatycznie kieruje wniosek do odpowiedniego approversa wg tabeli progów

### 3.2 Wybór dostawcy

**Dla zakupów powyżej 5 000 PLN** wymagane jest porównanie ofert:
- Poniżej 50 000 PLN: min. 3 oferty e-mail (dokumentowane w systemie ERP)
- Powyżej 50 000 PLN: formalne zapytanie ofertowe (RFQ) wysyłane do min. 5 dostawców z listy preferowanych

**Lista preferowanych dostawców** (AVL — Approved Vendor List) jest prowadzona przez Dział Zakupów. Zakup od dostawcy spoza AVL powyżej 10 000 PLN wymaga dodatkowej akceptacji Dyrektora Zakupów.

### 3.3 Złożenie zamówienia

1. Dział Zakupów wystawia oficjalne zamówienie (PO — Purchase Order) w systemie ERP
2. PO musi zawierać: nr dostawcy, opis, cena jednostkowa, ilość, termin dostawy, warunki płatności, centrum kosztów
3. Dostawca potwierdza odbiór PO mailem lub przez portal dostawców (supplier.firma-abc.pl)
4. Kopia PO wysyłana automatycznie do magazynu i działu finansowego

---

## 4. Odbiór towaru / usługi

### 4.1 Odbiór towarów

1. Magazyn przyjmuje towar, weryfikuje zgodność z PO (ilość, rodzaj)
2. Dokonuje wpisu w ERP — "Przyjęcie na magazyn" (GR — Goods Receipt)
3. Przekazuje towar do QA w celu kontroli wejściowej (jeśli dotyczy)
4. System automatycznie generuje zobowiązanie do zapłaty (3-way match: PO + GR + faktura)

### 4.2 Odbiór usług

1. Wnioskujący kierownik działu potwierdza wykonanie usługi w ERP (Service Entry Sheet)
2. Podpisuje protokół odbioru usługi z wykonawcą
3. Skan protokołu załączany do PO w systemie

---

## 5. Zakupy pilne (tryb awaryjny)

W sytuacjach awaryjnych (np. krytyczna awaria maszyny) dopuszcza się:
- Zakup bez wcześniejszego zapotrzebowania w ERP do wartości 2 000 PLN
- Kierownik Działu zatwierdza zakup telefonicznie/mailowo, a pracownik ma obowiązek retrospektywnie wprowadzić zapotrzebowanie w ERP w ciągu **24 godzin**
- Zakupy gotówkowe do 500 PLN możliwe z kasy firmowej za potwierdzeniem paragonem fiskalnym

---

## 6. Karty kredytowe firmowe

Karty kredytowe przyznawane są wybranym pracownikom (Dyrektorzy, Kierownicy) decyzją CFO:
- Limit miesięczny wg stanowiska (od 2 000 do 20 000 PLN)
- Dozwolone: podróże służbowe, reprezentacja, zakupy online do limitu
- Niedozwolone: wypłaty gotówki, zakupy prywatne, zakupy u podmiotów powiązanych
- Rozliczenie do 7 dni po zakończeniu miesiąca z załączeniem faktur w systemie Concur

---

## 7. Kontakt

- **Dział Zakupów:** zakupy@firma-abc.pl, wew. 250
- **Kontroler Finansowy:** controlling@firma-abc.pl, wew. 260
