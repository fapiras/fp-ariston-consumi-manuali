# Ariston FP

**0.4.0-beta.2 — integrazione autonoma per Ariston Lydos Hybrid.**

La beta.2 separa gli errori delle impostazioni dalla lettura dello stato:
se lo stato viene letto correttamente ma il successivo aggiornamento delle
impostazioni fallisce, temperatura e stato restano disponibili. Le impostazioni
conservano l'ultima cache, con attributi `impostazioni_aggiornate: false` ed
`errore_lettura_impostazioni`. Un errore nella lettura dello stato continua a
rendere indisponibili le entità: non si presenta una temperatura vecchia come
attuale. Questa correzione non risolve un rifiuto generale del cloud né gli
errori durante la prima inizializzazione e non aggiunge tentativi automatici.

Controlli completi e consumi su richiesta, derivati dal lavoro MIT di Mauro
Priori e fustom. Il client è incluso in uno spazio privato; Ariston NET non è
necessario al funzionamento. [Crediti e licenze](THIRD_PARTY_NOTICES.md).

## Consumi

- Un unico pulsante **Aggiorna consumi**, nessuna richiesta energetica all'avvio,
  periodica, durante il cambio mese o dopo i comandi dello scaldabagno.
- PDC, resistenza e totale separati per giornaliero, settimanale, mensile e annuale.
  Giornaliero e settimanale conservano le aggregazioni delle sequenze API.
- **Mese consumi**: selettore indipendente per dispositivo, con nomi come
  `Ottobre 2026`. Cambiare mese legge esclusivamente la cache locale.
- I mesi conclusi usano i punti della sequenza mensile. Il mese corrente somma
  i giorni conclusi e le fasce del giorno corrente e viene indicato come parziale.
- L'annuale contiene i dati disponibili nell'anno corrente, non la somma di
  tutta la sequenza storica restituita dal cloud. L'attributo `anno_riferimento`
  identifica l'anno; `mese_selezionato` identifica il mese.
- Se il cloud fallisce, l'ultima lettura valida rimane disponibile con data e
  indicazione che non è aggiornata. Dati mancanti non vengono trasformati in zero.

L'allineamento temporale è stato confrontato con un export datato dell'app:
22 punti corrispondono ai mesi conclusi, i giorni terminano al giorno precedente
e le fasce orarie hanno estremi UTC ogni due ore. L'associazione al calendario
usa questa regola e la data della richiesta, conservata in cache. Non si
riassegnano date ai valori memorizzati quando Home Assistant si riavvia.
Il file di riscontro personale e i consumi dell'utente non sono nel repository.
Ricontrollare il confronto con l'app se Ariston modifica il formato o i tempi
di consolidamento, in particolare a inizio mese. I consumi sono stime Ariston.

## Aggiornamento

In HACS il repository è sempre
`https://github.com/fapiras/fp-ariston-consumi-manuali`, categoria Integrazione.
Il nome visualizzato diventa **Ariston FP**. Il dominio `fp_ariston_consumi`,
le configurazioni e gli unique ID esistenti restano gli stessi.

Aggiorna informazioni, riscarica da `main` e riavvia Home Assistant. Premi una
volta **Aggiorna consumi** per caricare il calendario e i nuovi sensori. La
cache delle vecchie versioni non aveva date/valori separati sufficienti e viene
ignorata; non è necessario eliminare e ricreare l'integrazione.

Nuove entità (esempio dispositivo `Boiler A FP`):

| Funzione | ID normalmente creato |
|---|---|
| Selettore mese | `select.boiler_a_fp_mese_consumi` |
| PDC mese scelto | `sensor.boiler_a_fp_consumo_pdc_periodo_mensile` |
| Resistenza mese scelto | `sensor.boiler_a_fp_consumo_resistenza_periodo_mensile` |
| Totale mese scelto | `sensor.boiler_a_fp_consumo_periodo_mensile` |

Per gli altri periodi, i suffissi sono `giornaliero`, `settimanale`, `annuale`.
Gli ID personalizzati o migrati possono differire. Un grafico mensile deve
usare i due sensori del mese selezionato. Il nome del mese va mostrato accanto
al grafico; il totale si ottiene sommando PDC e resistenza. Uno stato sconosciuto
deve restare sconosciuto anche nel grafico.

## Controlli e migrazione

Conservati accensione, temperatura, modalità, GREEN/BOOST, notte, boost
permanente, antilegionella e anti cooling. Stato e impostazioni vengono letti
ogni 10 minuti per impostazione iniziale, con intervallo configurabile.

Per sostituire la vecchia integrazione seguire la
[guida di migrazione e ripristino](docs/MIGRAZIONE.md). Tenerla installata fino
al collaudo reale, disabilitandola durante le prove per evitare sessioni
concorrenti. I comandi e i valori del nuovo calendario richiedono ancora il
confronto sul proprio impianto, soprattutto per il secondo dispositivo.

## Test

Le suite includono piattaforme Home Assistant reali con cloud simulato,
calendario, cambio mese senza richieste cloud, cache e riavvio, separazione
dei due canali, errori e regressioni dei controlli originali.

```sh
pip install pytest-homeassistant-custom-component==0.13.375 requests ruff
ruff check custom_components tests
python -m pytest tests/unit tests/ha -q
```

I test Home Assistant richiedono Linux/Python 3.14. Le API Ariston sono non
ufficiali: un HTTP 500 viene segnalato, senza sostituire il risultato con zero.
