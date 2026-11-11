# FP Ariston Consumi Manuali

Integrazione sperimentale per Home Assistant, da aggiungere tramite HACS e utilizzare insieme ad [Ariston NET](https://github.com/mauropriori/ariston_net) 0.1.2 di Mauro Priori.

**Obiettivo:** leggere i consumi dei Lydos Hybrid esclusivamente quando si preme **Aggiorna consumi**, senza polling energetico periodico, né letture energetiche all'avvio.

Il componente aggiunge un dispositivo per ciascuno scaldabagno e i sensori per consumi giornalieri, settimanali, mensili e annuali in kWh, stato dell'ultima richiesta e data dell'ultimo aggiornamento. Non modifica Ariston NET, non cambia i setpoint, e non abilita il suo monitoraggio energetico. Riutilizza la connessione esistente del client Ariston autenticato.

## Installazione

1. Installa e configura Ariston NET 0.1.2, mantenendo disattivato il suo monitoraggio energetico.
2. In HACS: **⋮ → Repository personalizzati** → `https://github.com/fapiras/fp-ariston-consumi-manuali` → tipo **Integrazione**.
3. Installa **FP Ariston Consumi Manuali** e riavvia Home Assistant.
4. Vai in **Impostazioni → Dispositivi e servizi → Aggiungi integrazione** e seleziona FP Ariston Consumi Manuali.
5. Seleziona lo scaldabagno (Via Asti 4 oppure Sa Coixedda); ripeti per il secondo.
6. Sul dispositivo creato usa il pulsante **Aggiorna consumi**. Non sono effettuate letture automatiche dei consumi.

## Limiti e sicurezza

- L'endpoint Ariston `/api/v2/velis/reports/<gateway>?usages=Dhw&appId=com.remotethermo.velis` è **non ufficiale** e potrebbe essere modificato/disabilitato senza preavviso.
- I consumi sono stime aggregate del periodo, **non un contatore monotono dalla prima installazione**. Non usare direttamente questi sensori come `total_increasing` nella dashboard Energia.
- Se la lettura fallisce con HTTP 500, HTTP 429, timeout, DNS o risposta non valida, rimane l'ultimo dato valido, ma lo stato segnala l'errore; i comandi originali rimangono gestiti da Ariston NET.
- Il modulo richiama un metodo privato della libreria di Mauro Priori. Modifiche future di quella libreria potrebbero richiedere una revisione.
- È una **versione sperimentale**: i test del parser usano dati simulati; il cloud reale Ariston non è stato collaudato. Esegui un backup di Home Assistant prima dell'installazione e testa un solo dispositivo per volta.

## Crediti

Architettura basata sullo studio di [mauropriori/ariston_net](https://github.com/mauropriori/ariston_net), a sua volta derivato dal lavoro di fustom (MIT). Il formato dei report Lydos è documentato nel codice storico di [chomupashchuk/aquaariston-remotethermo-api](https://github.com/chomupashchuk/aquaariston-remotethermo-api).

Progetto non affiliato ad Ariston, Home Assistant o Mauro Priori. Licenza: MIT.
