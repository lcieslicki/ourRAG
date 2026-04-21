# Procedura obsługi awarii maszyn produkcyjnych — Firma ABC

**Dokument:** PROD-003  
**Wersja:** 3.1  
**Data aktualizacji:** 2024-01-05  
**Właściciel:** Dział Utrzymania Ruchu (UR)  

---

## 1. Cel dokumentu

Procedura określa sposób postępowania w przypadku awarii maszyn i urządzeń produkcyjnych, zasady zgłaszania usterek oraz priorytety obsługi przez Dział Utrzymania Ruchu.

---

## 2. Klasyfikacja awarii

| Priorytet | Opis sytuacji | Czas reakcji UR | Czas usunięcia |
|---|---|---|---|
| P1 — Krytyczny | Zatrzymanie całej linii produkcyjnej | 15 minut | 2 godziny |
| P2 — Wysoki | Zatrzymanie jednej maszyny, linia działa częściowo | 30 minut | 4 godziny |
| P3 — Normalny | Degradacja wydajności, maszyna działa | 2 godziny | 8 godzin |
| P4 — Niski | Usterka kosmetyczna, brak wpływu na produkcję | Następna zmiana | 48 godzin |

---

## 3. Procedura zgłoszenia awarii

### 3.1 Obowiązki operatora

W przypadku awarii operator NATYCHMIAST:
1. **Zatrzymuje maszynę** zgodnie z procedurą bezpiecznego zatrzymania (naciśnięcie e-stopu jeśli konieczne)
2. **Zabezpiecza strefę** — ustawia pachołki/taśmę ostrzegawczą
3. **Nie próbuje samodzielnie naprawiać** maszyny (zakaz bez kwalifikacji UR)
4. **Zgłasza awarię** przez jeden z kanałów:
   - System MES → zakładka "Awaria" → wypełnienie formularza (kod maszyny, opis objawów)
   - Telefon alarmowy UR: **wew. 500** (czynny 24/7)
   - Przycisk "Awaria" na panelu HMI (dla maszyn wyposażonych)

### 3.2 Obowiązki Mistrza Produkcji

1. Potwierdzenie zgłoszenia w MES w ciągu 5 minut
2. Ocena możliwości częściowego przełączenia produkcji na inną linię
3. Poinformowanie Planisty Produkcji o ryzyku opóźnień
4. Nadzór nad strefą bezpieczeństwa podczas naprawy

---

## 4. Procedura obsługi przez Utrzymanie Ruchu

### 4.1 Pierwsza interwencja

1. Technik UR przyjmuje zgłoszenie i potwierdza przyjęcie w MES
2. Diagnostyka na miejscu (max. 30 min dla P1, 1h dla P2)
3. Ocena: naprawa własna / konieczność zewnętrznego serwisu
4. Aktualizacja statusu w MES: szacowany czas naprawy (ETA)

### 4.2 Naprawa

- Technik UR dokumentuje w MES każdy krok naprawy (wymienione części, czynności)
- Części zamienne pobierane są z magazynu UR (lokalizacja: hala H, pomieszczenie UR-01)
- Części o wartości >5000 PLN wymagają akceptacji Kierownika UR przed zamówieniem
- Jeśli naprawa wymaga zewnętrznego serwisanta — Kierownik UR kontaktuje się z dostawcą wg listy preferowanych dostawców serwisowych (dokument UR-SL-001)

### 4.3 Przekazanie maszyny do produkcji

1. Technik UR wykonuje test rozruchowy (min. 15 minut pracy próbnej)
2. QA potwierdza jakość wyrobów po wznowieniu produkcji (First Article Inspection)
3. Mistrz Produkcji podpisuje odbiór maszyny w systemie MES
4. Technik UR zamyka zlecenie serwisowe — wpisuje przyczynę awarii wg klasyfikacji:
   - Zużycie eksploatacyjne
   - Błąd operatora
   - Wada materiałowa
   - Przyczyna zewnętrzna (zasilanie, media)
   - Nieznana

---

## 5. Konserwacja zapobiegawcza (TPM)

Maszyny objęte są harmonogramem konserwacji zapobiegawczej (TPM — Total Productive Maintenance):
- **Dzienna:** Czyszczenie i inspekcja przez operatora (checklist w MES, 15 min na początku zmiany)
- **Tygodniowa:** Smarowanie, sprawdzenie naprężeń przez UR (plan UR-TPM-W)
- **Miesięczna:** Przegląd techniczny przez UR + kalibracja (plan UR-TPM-M)
- **Roczna:** Przegląd generalny, wymiana podzespołów wear-out (plan UR-TPM-A)

Pominięcie konserwacji dziennej przez operatora musi być odnotowane przez Mistrza Produkcji z podaniem przyczyny.

---

## 6. Wskaźniki efektywności (KPI)

Dział UR raportuje miesięcznie do Dyrektora Produkcji:
- **MTBF** (Mean Time Between Failures) — cel: >200h dla maszyn klasy A
- **MTTR** (Mean Time To Repair) — cel: <2h dla awarii P1
- **OEE** (Overall Equipment Effectiveness) — cel: >85%
- Liczba awarii nieplanowanych vs. planowane przeglądy

---

## 7. Kontakt

- **UR Telefon alarmowy (24/7):** wew. 500
- **Kierownik UR:** ur.manager@firma-abc.pl, wew. 510
- **Magazyn części UR:** wew. 520
