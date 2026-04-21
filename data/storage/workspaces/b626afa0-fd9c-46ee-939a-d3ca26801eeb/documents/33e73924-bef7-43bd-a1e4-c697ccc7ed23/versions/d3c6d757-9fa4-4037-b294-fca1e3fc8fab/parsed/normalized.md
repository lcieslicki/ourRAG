# Procedura zarządzania dostawcami — Firma ABC

**Dokument:** LOG-002
**Wersja:** 1.6
**Data aktualizacji:** 2024-01-25
**Właściciel:** Dział Zakupów

---

## 1. Cel i zakres

Procedura określa zasady kwalifikacji, oceny i zarządzania dostawcami surowców, materiałów i usług dla Firmy ABC. Celem jest utrzymanie bazy sprawdzonych i wiarygodnych dostawców (AVL — Approved Vendor List).

---

## 2. Lista Preferowanych Dostawców (AVL)

AVL zawiera dostawców zatwierdzonych do współpracy. Podział:

| Status | Opis |
|---|---|
| Preferowany (P) | Dostawca z pełną kwalifikacją i pozytywną historią współpracy |
| Zatwierdzony (A) | Dostawca zakwalifikowany, bez historii lub krótka historia |
| Warunkowy (C) | Dostawca z zastrzeżeniami — zakup wymaga akceptacji Kierownika Zakupów |
| Zablokowany (B) | Zakaz zakupów — naruszenie warunków, problemy jakościowe |

AVL aktualizowana przez Dział Zakupów co kwartał i dostępna w systemie ERP.

---

## 3. Kwalifikacja nowego dostawcy

### 3.1 Inicjowanie kwalifikacji

Kwalifikację może zainicjować:
- Dział Zakupów (poszukiwanie alternatyw)
- Dział QA (wymagania jakościowe)
- Kierownik Działu (nowa kategoria zakupowa)

### 3.2 Etapy kwalifikacji

**Etap 1 — Ocena formalna (Dział Zakupów)**
- Weryfikacja w KRS / CEIDG
- Sprawdzenie w wykazie podatników VAT (Biała Lista)
- Analiza sytuacji finansowej (jeśli dostawca strategiczny — raport wywiadowni)
- Podpisanie NDA (jeśli wymagane)

**Etap 2 — Ocena jakościowa (Dział QA)**
- Wypełnienie przez dostawcę ankiety kwalifikacyjnej QA-F-040
- Audit dostawcy na miejscu (dla dostawców strategicznych — materiały klasy A)
- Ocena systemu zarządzania jakością (certyfikat ISO 9001, IATF 16949 itp.)
- Zamówienie i ocena próbek

**Etap 3 — Decyzja kwalifikacyjna**
- Ocena końcowa: Zakupy + QA + (opcjonalnie) Dział Techniczny
- Wpis do AVL z nadaniem statusu
- Podpisanie umowy ramowej (jeśli wartość współpracy >100 000 PLN/rok)

Czas kwalifikacji: **4–8 tygodni** dla standardowego dostawcy.

---

## 4. Ocena okresowa dostawców

### 4.1 Częstotliwość oceny

| Kategoria dostawcy | Częstotliwość |
|---|---|
| Strategiczny (>500 000 PLN/rok) | Co kwartał |
| Kluczowy (100 000–500 000 PLN/rok) | Co pół roku |
| Standardowy | Co rok |

### 4.2 Kryteria oceny

Ocena przeprowadzana w systemie ERP (formularz LOG-F-010):

| Kryterium | Waga |
|---|---|
| Jakość (PPM, reklamacje uznane) | 40% |
| Terminowość dostaw (OTD) | 30% |
| Cena (vs. rynek) | 20% |
| Współpraca / komunikacja | 10% |

Wynik końcowy 0–100 pkt:
- 80–100: Preferowany (P)
- 60–79: Zatwierdzony (A)
- 40–59: Warunkowy (C) + plan naprawczy
- Poniżej 40: Zablokowany (B)

### 4.3 Spotkania przeglądowe (Business Review)

Z dostawcami strategicznymi Dział Zakupów organizuje kwartalne spotkania Business Review, omawiające wyniki, plany i obszary do poprawy.

---

## 5. Obsługa problemów z dostawcą

### 5.1 Incydent jakościowy

Przy wystąpieniu reklamacji wobec dostawcy (uznana niezgodność):
1. QA wysyła do dostawcy 8D Request (żądanie raportu 8D) w ciągu 24h od uznania reklamacji
2. Dostawca ma 5 dni roboczych na przesłanie wstępnych działań korygujących
3. Pełny raport 8D: 30 dni
4. Brak raportu lub działań → status zmieniony na Warunkowy (C)
5. Powtarzalność problemu w ciągu 6 miesięcy → status Zablokowany (B)

---

## 6. Kontakt

- **Dział Zakupów (kwalifikacje dostawców):** zakupy.kwalifikacje@firma-abc.pl, wew. 255
- **QA (audity dostawców):** qa.dostawcy@firma-abc.pl, wew. 412
