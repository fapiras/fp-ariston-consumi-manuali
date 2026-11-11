# FP Ariston Consumi Manuali

**0.3.0-beta.4 — integrazione autonoma per Ariston Lydos Hybrid, da collaudare sul proprio impianto.**

La beta.4 sostituisce il report generico `velis/reports?usages=Dhw` con le sequenze
specifiche del Lydos Hybrid già usate dal client originale:
`remote/reports/…/consSequencesApi8?usages=DhwHeatingPumpElec%2CDhwResistorElec`.
Legge separatamente pompa di calore (codice 8) e resistenza (codice 9), identificando
i periodi tramite `p`, senza dipendere dall'ordine delle righe. Un totale è
pubblicato solo se entrambe le componenti hanno elenchi validi della stessa
lunghezza. Uno zero esplicito è valido; una componente mancante non vale zero.
L'attributo `dettaglio_periodo` contiene i valori delle due sequenze in kWh per
confrontarli con l'app. Gli estremi dei periodi non sono ancora certificati:
non confrontare un totale di intervallo con un singolo mese selezionato nell'app.
Le cache delle beta precedenti vengono ignorate, per non mantenere gli zero
restituiti dalla vecchia richiesta generica. Se il nuovo endpoint restituisce
HTTP 500, l'errore viene mostrato senza ripiegare silenziosamente sul vecchio
report zero. Nessuna richiesta energetica parte automaticamente.

La beta.3 gestisce i report parziali: se gli elenchi giornaliero e settimanale
sono vuoti, mensile e annuale vengono comunque letti e salvati quando validi.
Lo stato diventa `aggiornato_parzialmente`. Un periodo vuoto rimane sconosciuto
oppure conserva l'ultimo dato valido, segnalato come non aggiornato e con la
propria data di lettura. I mancanti non diventano zero. Gli attributi
`periodi_aggiornati`, `periodi_non_disponibili` e `ultimo_successo_periodo_utc`
permettono di distinguere le letture recenti da quelle conservate. La data
generale dell'ultimo successo indica l'ultima lettura di almeno un periodo valido.
Se tutti i periodi sono vuoti oppure il formato è malformato, la lettura dà errore
e conserva lo snapshot precedente. Il collaudo dei valori reali resta necessario.

La beta.2 distingue risposta vuota, numero di periodi inatteso e consumi mancanti.
Se la lettura fallisce, copia il messaggio esatto e l'attributo `struttura_report`
del sensore **Stato lettura consumi**. Contiene solo tipi, conteggi e nomi di campi
predefiniti, senza valori cloud o identificativi. Questo aggiornamento aggiunge
diagnostica: non certifica né ripara ancora la lettura sul dispositivo reale.

Fork di Ariston NET di Mauro Priori / fustom, con client incluso in uno spazio
privato. Nessuna dipendenza da `custom_components/ariston_net` e nessun accesso
al suo client durante il funzionamento. Licenza MIT e crediti conservati:
[provenienza](THIRD_PARTY_NOTICES.md).

## Funzioni

- Temperatura corrente e desiderata, docce stimate, riscaldamento e ciclo
  antilegionella; entità `water_heater` e comandi di accensione.
- Modalità del Lydos (GREEN, BOOST e le altre offerte dal client), notte,
  boost permanente, antilegionella, anti cooling e relative soglie/orari.
- Stato e impostazioni letti ogni 10 minuti per impostazione iniziale
  (intervallo configurabile, minimo 60 secondi).
- **Aggiorna consumi**: una lettura manuale dei totali dei quattro periodi
  restituiti dal cloud. Nessuna lettura energetica all'avvio, su timer,
  dopo un comando, o attraverso un generico aggiornamento di un sensore.
- Cache locale e ultima lettura valida mantenute in caso di errore cloud;
  un errore energetico non mette in errore il coordinatore dei comandi.
  Eventuali blocchi del cloud sull'intero account possono comunque coinvolgere
  anche le altre richieste.

I totali sono fotografie dei periodi API, **non** il consumo dalla prima accensione.
Non vengono presentati come contatori `total_increasing` né uniti alle vecchie
statistiche di pompa di calore e resistenza. L'endpoint energetico è storico e
non ufficiale: può restituire HTTP 500 o non essere disponibile per un account.
Una risposta incompleta non viene trasformata in un consumo pari a zero.

## Installazione e sostituzione

In HACS aggiungi il repository personalizzato
`https://github.com/fapiras/fp-ariston-consumi-manuali`, categoria **Integrazione**.
Il repository contiene un solo dominio, `fp_ariston_consumi`.
Riavvia Home Assistant e aggiungi **FP Ariston Consumi Manuali** da Dispositivi
e servizi, accedendo direttamente ad Ariston e selezionando ogni scaldabagno.

Se è già installata la 0.2.0, l'aggiornamento copia una sola volta la configurazione
della corrispondente voce Ariston NET, se presente; poi funziona con il proprio
client. Se manca quella configurazione viene richiesto un nuovo accesso.
Non cancellare prima le voci FP esistenti se vuoi conservare cache e ID energetici.

**Conserva Mauro installato fino al collaudo positivo di entrambi i dispositivi.**
Disabilita temporaneamente le sue voci durante il test, per evitare sessioni
cloud concorrenti. Gli ID FP hanno un suffisso FP e unique ID indipendenti.

Segui il [piano completo di migrazione e ripristino](docs/MIGRAZIONE.md), che spiega
come riprendere gli `entity_id` della dashboard, gestire gli storici, aggiornare
i riferimenti alle automazioni e quando disinstallare il vecchio pacchetto.

## Verifica

La suite comprende parser rigoroso, test originali di resilienza e BOOST,
test con il vero ambiente Home Assistant e cloud simulato: caricamento piattaforme,
comandi, assenza di polling energetico, cache/riavvio, errori, doppia pressione,
account condiviso, configurazione e passaggio dalla 0.2.0.

```sh
pip install pytest-homeassistant-custom-component==0.13.375 requests ruff
ruff check custom_components tests
pytest tests/unit tests/ha -q
```

I test di Home Assistant si eseguono su Linux con Python 3.14. La disponibilità
dell'API, i valori restituiti e i comandi sui due apparecchi reali devono ancora
essere verificati dall'utente. **Codice pubblicato e test automatici non equivalgono
a migrazione conclusa né ad autorizzazione a cancellare subito Mauro.**
