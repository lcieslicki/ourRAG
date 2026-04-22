# Procedura zgłaszania i obsługi incydentów IT (Helpdesk) — Firma ABC

**Dokument:** IT-002  
**Wersja:** 2.2  
**Data aktualizacji:** 2023-10-15  
**Właściciel:** Dział IT  

---

## 1. Cel dokumentu

Procedura opisuje sposób zgłaszania problemów technicznych przez pracowników oraz proces ich obsługi przez Dział IT (Helpdesk).

---

## 2. Kanały zgłaszania

| Kanał | Adres / numer | Dostępność | Priorytet |
|---|---|---|---|
| Portal Helpdesk | helpdesk.firma-abc.pl | 24/7 | Wszystkie |
| E-mail | it-helpdesk@firma-abc.pl | 24/7 | P2–P4 |
| Telefon | wew. 300 | Pn–Pt 07:00–20:00 | P1–P2 |
| Osobista wizyta | Pokój IT-01, budynek A | Pn–Pt 08:00–16:00 | P3–P4 |

**Zalecany kanał:** Portal Helpdesk — umożliwia śledzenie statusu zgłoszenia.

---

## 3. Priorytety zgłoszeń

| Priorytet | Opis | Czas pierwszej reakcji | Czas rozwiązania |
|---|---|---|---|
| P1 — Krytyczny | Brak dostępu do kluczowego systemu (ERP, MES) dla >5 osób | 15 minut | 4 godziny |
| P2 — Wysoki | Problem jednego użytkownika blokujący pracę | 1 godzina | 8 godzin |
| P3 — Normalny | Problem utrudniający, ale nieblokujący pracę | 4 godziny | 2 dni robocze |
| P4 — Niski | Pytanie, prośba, zmiana | 1 dzień roboczy | 5 dni roboczych |

---

## 4. Jak poprawnie opisać zgłoszenie

Dobre zgłoszenie przyspiesza rozwiązanie. Należy podać:
1. **Co nie działa** — opis problemu (nie "komputer nie chodzi", lecz "po uruchomieniu programu IFS pojawia się błąd 'Connection timeout'")
2. **Od kiedy** — kiedy problem wystąpił po raz pierwszy
3. **Czy coś się zmieniło** — nowe oprogramowanie, aktualizacja, przeprowadzka biura
4. **Jak często** — zawsze / sporadycznie / tylko przy konkretnej czynności
5. **Numer zasobu** (Asset Tag) — naklejka na sprzęcie, np. ABC-PC-1234
6. **Pilność** — czy blokuje pracę

---

## 5. Typowe problemy i samoobsługa

### 5.1 Reset hasła

Pracownik może zresetować hasło samodzielnie przez:
- Portal: haslo.firma-abc.pl (wymaga wcześniejszej rejestracji telefonu do MFA)
- Alternatywnie: kontakt z Helpdeskiem telefonicznie po weryfikacji tożsamości (imię, nazwisko, dział, data urodzenia)

### 5.2 Drukarka nie drukuje

1. Sprawdź czy drukarka jest włączona i ma papier
2. Uruchom ponownie kolejkę wydruku (Usługi → Bufor wydruku → Uruchom ponownie)
3. Odinstaluj i zainstaluj sterownik drukarki z portalu IT → Oprogramowanie → Drukarki
4. Jeśli nie pomaga — zgłoś ticket P3

### 5.3 Brak dostępu do folderu sieciowego

Wnioski o dostęp do zasobów sieciowych składa **przełożony pracownika** przez portal Helpdesk (formularz "Zarządzanie dostępami"). Pracownik nie może wnioskować o dostęp samodzielnie.

---

## 6. SLA i eskalacja

Jeśli zgłoszenie nie zostało rozwiązane w deklarowanym czasie:
- **Po 150% SLA** — system automatycznie eskaluje do Kierownika IT
- **Po 200% SLA** — eskalacja do CTO

Pracownik może w każdej chwili eskalować zgłoszenie ręcznie przez portal Helpdesk (przycisk "Eskaluj zgłoszenie") z podaniem uzasadnienia.

---

## 7. Satysfakcja z obsługi

Po zamknięciu zgłoszenia pracownik otrzymuje e-mail z ankietą satysfakcji (1–5 gwiazdek + komentarz). Udział jest dobrowolny, ale pomaga poprawiać jakość usług IT.

---

## 8. Kontakt

- **Portal Helpdesk:** helpdesk.firma-abc.pl
- **E-mail:** it-helpdesk@firma-abc.pl
- **Telefon:** wew. 300 (Pn–Pt, 07:00–20:00)
