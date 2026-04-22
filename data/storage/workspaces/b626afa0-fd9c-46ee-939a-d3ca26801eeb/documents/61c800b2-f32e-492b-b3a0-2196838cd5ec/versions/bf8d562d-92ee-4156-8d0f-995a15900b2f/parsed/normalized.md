# Polityka bezpieczeństwa IT — Firma ABC

**Dokument:** IT-001
**Wersja:** 3.0
**Data aktualizacji:** 2024-01-20
**Właściciel:** Dział IT / CISO

---

## 1. Cel i zakres

Dokument określa zasady bezpieczeństwa systemów informatycznych obowiązujące wszystkich pracowników, kontrahentów i gości korzystających z infrastruktury IT Firmy ABC.

---

## 2. Hasła i uwierzytelnianie

### 2.1 Wymagania dotyczące haseł

Hasła do systemów firmowych muszą spełniać:
- Minimum **12 znaków**
- Co najmniej jedna wielka litera, jedna cyfra i jeden znak specjalny
- Brak imion, dat urodzenia, nazwy firmy
- Zmiana hasła co **90 dni** (wymuszana przez system)
- Zakaz używania 12 ostatnich haseł (historia haseł)

### 2.2 Uwierzytelnianie dwuskładnikowe (MFA)

MFA jest obowiązkowe dla:
- Wszystkich systemów dostępnych z zewnątrz (VPN, poczta przez Outlook Web, ERP przez internet)
- Kont administratorów systemów
- Dostępu do danych osobowych (RODO)

Obsługiwane metody MFA: Microsoft Authenticator (preferowany), SMS (dopuszczony), klucz sprzętowy FIDO2 (dla administratorów).

---

## 3. Urządzenia i stacje robocze

### 3.1 Zasady korzystania ze sprzętu firmowego

- Sprzęt firmowy służy wyłącznie do celów służbowych
- Instalacja oprogramowania dozwolona wyłącznie przez Helpdesk IT (wew. 300)
- Zakaz podłączania prywatnych nośników USB bez zgody IT
- Stacja robocza musi być zablokowana przy opuszczaniu stanowiska (skrót: Win+L)
- Szyfrowanie dysków (BitLocker) jest włączone domyślnie — wyłączanie zabronione

### 3.2 Praca zdalna

- Dostęp zdalny wyłącznie przez VPN firmowy (GlobalProtect)
- Zakaz korzystania z publicznych sieci WiFi bez aktywnego VPN
- Prywatny komputer do pracy zdalnej wymaga uprzedniej rejestracji w IT i instalacji agenta bezpieczeństwa (CrowdStrike)

---

## 4. Poczta elektroniczna i komunikacja

- Poczta firmowa (@firma-abc.pl) służy wyłącznie do celów służbowych
- Zakaz przesyłania danych wrażliwych (dane osobowe, dane finansowe, sekrety handlowe) niezaszyfrowanym mailem
- Załączniki powyżej 25 MB: korzystać z firmowego SharePoint lub OneDrive
- Phishing: podejrzane wiadomości należy przekazać na adres **phishing@firma-abc.pl** i nie klikać linków
- Komunikatory: oficjalnym narzędziem jest Microsoft Teams. Zakaz używania prywatnych komunikatorów (WhatsApp, Messenger) do spraw służbowych

---

## 5. Dane i poufność

### 5.1 Klasyfikacja danych

| Klasa | Przykłady | Sposób przechowywania |
|---|---|---|
| Publiczne | Materiały marketingowe, katalogi | Bez ograniczeń |
| Wewnętrzne | Procedury, instrukcje, prezentacje | Sieć firmowa, SharePoint |
| Poufne | Dane klientów, wyniki finansowe, umowy | SharePoint + szyfrowanie |
| Ściśle tajne | Dane osobowe, IP, hasła | Szyfrowane, dostęp ograniczony |

### 5.2 Zasada minimalnego dostępu

Pracownicy mają dostęp wyłącznie do systemów i danych niezbędnych do wykonywania swoich obowiązków. Wnioski o nowe dostępy składane przez przełożonego przez system IT (it-helpdesk@firma-abc.pl).

---

## 6. Incydenty bezpieczeństwa

### 6.1 Co zgłaszać natychmiast

- Podejrzenie włamania na konto (nieznane logowania, zmienione hasło)
- Zagubienie lub kradzież sprzętu firmowego
- Otwarcie podejrzanego załącznika / kliknięcie w phishing
- Dostrzeżenie nieautoryzowanej osoby przy komputerze
- Zaszyfrowanie plików (ransomware)

### 6.2 Jak zgłaszać

- **Telefon (24/7):** wew. 500 lub +48 61 555 0500 (zewnętrzny)
- **E-mail:** security@firma-abc.pl
- **Nie:** opóźniać zgłoszenia w obawie przed konsekwencjami — zgłoszenie chroni pracownika

Pracownik zgłaszający incydent w dobrej wierze jest chroniony przed negatywnymi konsekwencjami służbowymi.

---

## 7. Konsekwencje naruszenia polityki

Naruszenie polityki bezpieczeństwa IT może skutkować:
- Upomnieniem lub naganą
- Czasowym odebraniem dostępów
- Rozwiązaniem umowy o pracę w przypadku poważnych naruszeń
- Odpowiedzialnością karną (art. 267–269 Kodeksu Karnego) w przypadku działania umyślnego

---

## 8. Kontakt

- **Helpdesk IT:** it-helpdesk@firma-abc.pl, wew. 300
- **Bezpieczeństwo IT (CISO):** security@firma-abc.pl, wew. 320
- **Zgłoszenia awaryjne 24/7:** wew. 500
