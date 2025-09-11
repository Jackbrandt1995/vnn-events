(async function(){
  const FEED_URL = "https://jackbrandt1995.github.io/vnn-events/events.json";;
  const root = document.getElementById("vnn-events-root");
  root.innerHTML = `<div class="vnn-loading">Loading events…</div>`;

  function fmtDate(dstr){
    const d = new Date(dstr);
    return d.toLocaleString([], { month:"short", day:"numeric", weekday:"short", hour:"numeric", minute:"2-digit" });
  }

  function groupByDate(events){
    const map = {};
    events.forEach(e=>{
      const key = new Date(e.start).toISOString().slice(0,10);
      (map[key] ||= []).push(e);
    });
    return map;
  }

  function render(events){
    const states = [...new Set(events.map(e=>e.state).filter(Boolean))].sort();
    const cities = [...new Set(events.map(e=>e.city).filter(Boolean))].sort();

    const controls = document.createElement("div");
    controls.className = "vnn-controls";
    controls.innerHTML = `
      <label>State:
        <select id="vnn-filter-state">
          <option value="">All</option>
          ${states.map(s=>`<option>${s}</option>`).join("")}
        </select>
      </label>
      <label>City:
        <select id="vnn-filter-city">
          <option value="">All</option>
          ${cities.map(c=>`<option>${c}</option>`).join("")}
        </select>
      </label>
    `;

    const list = document.createElement("div");
    list.className = "vnn-list";

    function draw(stateVal="", cityVal=""){
      const filtered = events.filter(e => (!stateVal || e.state===stateVal) && (!cityVal || e.city===cityVal));
      const grouped = groupByDate(filtered);
      const days = Object.keys(grouped).sort();
      list.innerHTML = days.length ? "" : `<div class="vnn-empty">No events found within the next 60 days.</div>`;
      days.forEach(day=>{
        const dayWrap = document.createElement("section");
        dayWrap.className = "vnn-day";
        const dayHdr = new Date(day+"T00:00:00").toLocaleDateString([], { weekday:"long", month:"long", day:"numeric" });
        dayWrap.innerHTML = `<h3 class="vnn-day-title">${dayHdr}</h3>`;
        grouped[day]
          .sort((a,b)=>(a.start.localeCompare(b.start) || (a.city||"").localeCompare(b.city||"")))
          .forEach(e=>{
            const loc = [e.venue_name, e.city, e.state].filter(Boolean).join(", ");
            const cost = e.cost ? ` • ${e.cost}` : "";
            const url = e.registration_url ? `<a class="vnn-link" href="${e.registration_url}" target="_blank" rel="noopener">Details</a>` : "";
            const desc = e.description ? `<div class="vnn-desc">${e.description}</div>` : "";
            const card = document.createElement("article");
            card.className = "vnn-card";
            card.innerHTML = `
              <div class="vnn-time">${fmtDate(e.start)}</div>
              <div class="vnn-title">${e.title}</div>
              <div class="vnn-meta">${loc}${cost}</div>
              <div class="vnn-cta">${url}</div>
            `;
            dayWrap.appendChild(card);
          });
        list.appendChild(dayWrap);
      });
    }

    controls.addEventListener("change", () => {
      const st = controls.querySelector("#vnn-filter-state").value;
      const ct = controls.querySelector("#vnn-filter-city").value;
      draw(st, ct);
    });

    root.innerHTML = "";
    root.appendChild(controls);
    root.appendChild(list);
    draw();
  }

  try {
    const res = await fetch(FEED_URL, {cache:"no-store"});
    const data = await res.json();
    render(data.events || []);
  } catch (e) {
    root.innerHTML = `<div class="vnn-error">Could not load events. Please try again later.</div>`;
  }
})();
