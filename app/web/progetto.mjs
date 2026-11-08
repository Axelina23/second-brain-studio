// Finestra "Nuovo progetto" (e "Aspetto del progetto" per quelli esistenti): nome,
// descrizione, fondo della piastrella ed emblema dipinto, con anteprima dal vivo.
// Il progetto lo crea ponte.crea_progetto: Progetti/<Nome>/CLAUDE.md + Output/ + voce in INDICE.
import { html, useState } from "./vendor/preact-htm.mjs";
import { Emblema, EMBLEMI, nomeEmblema, FONDI, FONDI_EXTRA, MOTIVI, Motivo, fondoPiastrella, emblemaPer } from "./icone.mjs";

export function DialogoProgetto({ api, progetto, chiudi, fatto, apriChat }) {
  const modifica = !!progetto;
  const [nome, setNome] = useState(progetto ? progetto.nome : "");
  const [descrizione, setDescrizione] = useState("");
  const [emblema, setEmblema] = useState((progetto && progetto.aspetto && progetto.aspetto.emblema) || (progetto ? emblemaPer(progetto.nome) : "f:light-bulb"));
  const [motivo, setMotivo] = useState((progetto && progetto.aspetto && progetto.aspetto.motivo) || "smalto");
  const [fondo, setFondo] = useState((progetto && fondoPiastrella(progetto.nome, progetto.aspetto)) || FONDI[0]);
  const [errore, setErrore] = useState("");
  const [lavoro, setLavoro] = useState(false);

  const conferma = async (conClaude) => {
    setLavoro(true); setErrore("");
    const r = modifica ? await api("cambia_aspetto", progetto.percorso, fondo, emblema, motivo)
      : await api("crea_progetto", nome, descrizione, fondo, emblema, motivo);
    setLavoro(false);
    if (r.errore) { setErrore(r.errore); return; }
    fatto(modifica ? "Aspetto del progetto aggiornato" : `Progetto "${r.nome}" creato`);
    if (conClaude) apriChat("nuova", null, `Ho appena creato il progetto "${r.nome}"${descrizione ? `: ${descrizione}` : ""}. Fammi qualche domanda per capire obiettivi e prossimi passi, poi aggiorna ${r.percorso}.`);
  };

  return html`<div class="velo" onClick=${(e) => e.target === e.currentTarget && chiudi()}>
    <div class="dialogo dialogo-progetto" role="dialog" aria-modal="true" aria-label=${modifica ? "Aspetto del progetto" : "Nuovo progetto"}>
      <h3>${modifica ? `Aspetto di ${progetto.nome}` : "Nuovo progetto"}</h3>
      <div class="progetto-corpo">
        <div class="progetto-anteprima">
          <div class="piastrella anteprima" style=${`--fondo:${fondo}`}>
            <${Motivo} motivo=${motivo} /><${Emblema} nome=${nome} emblema=${emblema} /><span class="nome">${nome || "Nome"}</span><span class="eta">oggi</span>
          </div>
        </div>
        <div class="progetto-campi">
          ${!modifica && html`
            <label class="etichetta-campo">Nome
              <input class="campo" value=${nome} maxLength="40" onInput=${(e) => setNome(e.target.value)} placeholder="Es. Orto sul balcone" autofocus /></label>
            <label class="etichetta-campo"><span>Di cosa si tratta <span class="facolt">· facoltativo</span></span>
              <input class="campo" value=${descrizione} maxLength="140" onInput=${(e) => setDescrizione(e.target.value)} placeholder="Una riga: finisce nell'indice del second brain" /></label>`}
          <div class="etichetta-campo">Colore</div>
          <div class="fondi" role="radiogroup" aria-label="Colore della piastrella">${[...FONDI, ...FONDI_EXTRA].map((c) => html`<button role="radio" aria-checked=${fondo === c}
            class=${`fondo-scelta ${fondo === c ? "scelto" : ""}`} style=${`background:${c}`} onClick=${() => setFondo(c)} aria-label=${c}></button>`)}</div>
          <div class="etichetta-campo">Motivo</div>
          <div class="motivi" role="radiogroup" aria-label="Motivo dello sfondo">${MOTIVI.map(([k, n]) => html`<button role="radio" aria-checked=${motivo === k}
            class=${`motivo-scelta ${motivo === k ? "scelto" : ""}`} style=${`--fondo:${fondo}`} onClick=${() => setMotivo(k)} title=${n}>
            <${Motivo} motivo=${k} /><span>${n}</span></button>`)}</div>
          <div class="etichetta-campo">Emblema</div>
          <div class="emblemi" role="radiogroup" aria-label="Emblema">${EMBLEMI.map((k) => html`<button role="radio" aria-checked=${emblema === k}
            class=${`emblema-scelta ${emblema === k ? "scelto" : ""}`} onClick=${() => setEmblema(k)} title=${nomeEmblema(k)}>
            <${Emblema} emblema=${k} /></button>`)}</div>
        </div>
      </div>
      ${errore && html`<div class="messaggio">${errore}</div>`}
      <div class="azioni">
        <button class="btn fantasma" onClick=${chiudi}>Annulla</button>
        ${!modifica && html`<button class="btn" disabled=${lavoro || !nome.trim()} onClick=${() => conferma(true)}>Crea e parlane con Claude</button>`}
        <button class="btn primario" disabled=${lavoro || (!modifica && !nome.trim())} onClick=${() => conferma(false)}>${modifica ? "Salva" : "Crea progetto"}</button>
      </div>
    </div></div>`;
}
