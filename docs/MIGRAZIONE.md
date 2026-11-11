# Migrazione controllata e ripristino

La 0.3.0-beta.1 è una versione autonoma da collaudare sul proprio impianto.
I test con risposte simulate non certificano la disponibilità delle API Ariston
per il singolo account. Non disinstallare Ariston NET prima del collaudo positivo.

## 1. Prepara il ripristino

1. Crea e scarica un backup completo Home Assistant, con configurazione, registri,
   dashboard e database Recorder. Se usi un database esterno, salvalo separatamente.
2. Esporta lo YAML della plancia. Registra tutti gli `entity_id`, compresi quelli
   nelle espressioni JavaScript, nei grafici e nelle automazioni.
3. Annota versione e impostazioni di Ariston NET, credenziali disponibili, aree,
   entità disabilitate e automazioni che usano `device_id`.
4. Conserva una copia della cartella `custom_components/ariston_net` e della
   precedente `fp_ariston_consumi` 0.2.0 se già installata. Il vecchio codice FP
   è anche nel commit `1cd4f4e0e1d529944ef8edfef91fba4cf9dd8644` di questo repository.

## 2. Prova FP senza eliminare Mauro

1. Disabilita temporaneamente le voci Ariston NET che usano lo stesso account.
   Lascia installati file e configurazioni per il ripristino. Non tenere due
   integrazioni attive sullo stesso account: i client sono indipendenti e possono
   disturbarsi con login e limiti cloud anche se i nomi delle entità sono distinti.
2. In HACS, repository personalizzati, categoria Integrazione, usa
   `https://github.com/fapiras/fp-ariston-consumi-manuali`.
   Installa la versione pubblicata e riavvia Home Assistant.
3. Se avevi FP 0.2.0, le sue voci vengono aggiornate alla configurazione 2:
   copiano una sola volta la configurazione della corrispondente voce Mauro,
   senza modificarla. Se questa non esiste, FP richiede il proprio accesso.
   Non è necessario cancellare le vecchie voci FP; cache e nomi delle sue entità
   energetiche vengono conservati ove presenti.
4. Per una nuova configurazione: Impostazioni → Dispositivi e servizi → Aggiungi
   integrazione → FP Ariston Consumi Manuali. Inserisci le credenziali Ariston e
   scegli lo scaldabagno. Ripeti per il secondo. Uno stesso account condivide un
   client dentro FP; account diversi rimangono separati.
5. Il dispositivo FP ha normalmente il suffisso **FP**. Controlla gli ID effettivi:
   Home Assistant può aggiungere suffissi o mantenere nomi personalizzati.
   Crea una copia della vista con le entità FP per il collaudo.

## 3. Collaudo obbligatorio per ciascuno scaldabagno

- Confronta temperatura corrente, obiettivo, docce stimate e stato riscaldamento
  con l'app Ariston.
- Prova accensione/spegnimento e una variazione reversibile dell'obiettivo;
  ripristina il valore iniziale e verifica la successiva lettura dal cloud.
- Prova GREEN, la modalità abituale e BOOST temporaneo; controlla anche il ritorno
  successivo. La convergenza del cloud può richiedere tempo.
- Controlla notte, boost permanente, antilegionella, ciclo in corso, anti cooling
  e soglia. Per le protezioni è sufficiente confrontare valori e disponibilità:
  non disattivarle solo per collaudare il software. Verifica anche le eventuali
  altre impostazioni usate (orari notte, limiti temperatura).
- Prima di premere il pulsante, i consumi devono essere sconosciuti oppure
  ripristinati dalla cache: nessuna richiesta energetica all'avvio o periodica.
- Premi **Aggiorna consumi** una volta; confronta totali e periodo con l'app.
  Se compare HTTP 500, 429 o risposta non valida, il collaudo energetico **non è
  superato**. I comandi devono restare operativi e l'ultimo dato valido invariato.
- Ricarica/riavvia e verifica cache, data dell'ultima lettura e nessuna lettura
  energetica automatica. Riavvio e ricaricamento non sono pulsanti di aggiornamento.

Non continuare alla disinstallazione se una funzione necessaria non passa.

## 4. Riprendi gli ID originali dopo il collaudo

La dashboard è collegata agli `entity_id`, non al dominio interno dell'integrazione.
FP usa unique ID propri; non assume la proprietà delle entità Mauro.

1. Esegui un secondo backup, annotando la tabella vecchio ID → entità FP verificata.
2. Quando i due dispositivi sono collaudati, rimuovi le vecchie voci Ariston NET
   da Dispositivi e servizi, conservando ancora il suo pacchetto HACS e il backup.
   Non cancellare database, storico o statistiche.
3. Se qualche vecchio ID è ancora riservato, controlla le entità orfane della
   vecchia integrazione prima di liberarlo. Non modificare `.storage` a mano.
4. Dalle impostazioni delle entità FP assegna esattamente i vecchi `entity_id`,
   una corrispondenza verificata alla volta. Se HA segnala ID già usato, fermati
   e risolvi il conflitto; non accettare un suffisso `_2` come ID definitivo.
5. Riutilizza la dashboard originale e controlla pop-up, scheda temperatura,
   selettore modalità, interruttori e grafici. Aggiungi i nuovi pulsanti consumi.
6. Ricontrolla automazioni e scene: i riferimenti per `entity_id` possono restare
   validi; quelli basati su `device_id`, dispositivi o trigger dell'integrazione
   devono essere ricollegati ai nuovi dispositivi FP.
7. Dopo questa verifica completa puoi disinstallare `mauropriori/ariston_net`
   da HACS e riavviare. Non serve più a FP.

### Storico e statistiche: cosa si conserva

Usare gli stessi ID e le stesse unità offre continuità alla dashboard e permette
di ritrovare lo storico Recorder ancora presente, entro la retention configurata.
Il ripristino completo resta il riferimento sicuro: la fusione dello storico di
due entità già registrate non è automatica né garantita.

**Non rinominare prima le entità originali in `*_backup` per liberare gli ID**:
HA può spostare anche lo storico e le statistiche al nuovo nome. Nel sorgente
[Recorder 2026.11.1](https://github.com/home-assistant/core/blob/2026.11.1/homeassistant/components/recorder/entity_registry.py)
la rinomina aggiorna entrambi. La procedura sopra mantiene gli originali fermi
fino alla rimozione delle voci, poi riutilizza i loro ID.

I nuovi totali giornaliero/settimanale/mensile/annuale sono fotografie dei periodi
restituiti dall'API. Non sono un contatore crescente dalla prima installazione,
non usano `total_increasing` e non vengono fusi con statistiche di vecchi sensori
che separavano pompa di calore e resistenza. Una lettura manuale non ricostruisce
retroattivamente dati mancanti. Gli estremi esatti dei periodi vanno verificati
nell'app; non si presume che coincidano con il mese o l'anno di calendario.

## Ripristino

- **Prima della rimozione delle voci Mauro:** disabilita FP, riabilita Mauro e
  ripristina la vista originale. Evita di lasciare attive entrambe le integrazioni.
- **Dopo rimozione o rinomina degli ID:** il metodo affidabile è ripristinare il
  backup completo immediatamente precedente alla migrazione, compreso il database.
  Reinstallare solo il codice non ricrea registri, nomi e storico.
- Per tornare alla FP 0.2.0 serve anche il backup precedente all'aggiornamento:
  la configurazione versione 2 non è leggibile dal vecchio componente.

Non modificare direttamente il database o i registri interni per tentare fusioni.
