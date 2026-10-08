import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
from database import portal_db
from auth.session import current_patient
from services.audit import audit
from services.timeutil import to_local, fmt_long, fmt_short, utcnow, MESI
from config import FACILITY_NAME, FACILITY_PHONE

dash.register_page(__name__, path="/patient/portal", name="Portale Paziente")


def _field(label, value, md=4):
    return dbc.Col(html.Div([html.Div(label, className="field-label"),
                             html.Div(value if value not in (None, "") else "—", className="field-value")],
                            className="field-card"), md=md, className="mb-2")


def layout(**kwargs):
    me = current_patient()
    if not me:
        return dcc.Location(id="portal-redir", href="/patient/login")
    aid, pid = me
    prof = portal_db.profile(aid, pid)
    docs = portal_db.documents(pid)
    appts = portal_db.appointments(pid)
    upcoming = [a for a in appts if a["status"] == "booked" and a["start_at"] >= utcnow()]
    audit("portal_view", "patient", aid, resource="patient", resource_id=pid)

    full = f"{prof['first_name']} {prof['last_name']}".strip() or prof["code"]
    initials = "".join(x[0] for x in full.split()[:2]).upper()
    nxt = upcoming[0] if upcoming else None

    return html.Div([
        html.Div([
            html.Img(src="/assets/logo.png", style={"height": "38px"}),
            html.Div([html.Span(prof["email"], style={"fontSize": "13px", "color": "#6B7280",
                                                     "marginRight": "14px"}),
                      html.A("↩  Esci", href="/auth/logout", className="btn btn-outline-secondary btn-sm")]),
        ], className="portal-top"),

        html.Div([
            html.Div(initials, className="portal-avatar"),
            html.Div([html.H2(full),
                      html.Div(f"Codice paziente {prof['code']}  ·  {FACILITY_NAME}", className="sub")],
                     style={"flex": "1"}),
            html.Div([html.B(len(docs)), "referti"], className="portal-kpi"),
            html.Div([html.B(len(upcoming)), "appuntamenti"], className="portal-kpi"),
            html.Div([html.B(fmt_short(nxt["start_at"])[:5] if nxt else "—"), "prossimo"],
                     className="portal-kpi"),
        ], className="portal-hero"),

        dbc.Tabs([
            dbc.Tab(_tab_profile(prof), label="👤  Anagrafica", tab_id="anag"),
            dbc.Tab(_tab_documents(docs), label="📁  Cartella clinica", tab_id="docs"),
            dbc.Tab(_tab_appointments(appts), label="📅  Appuntamenti", tab_id="appt"),
        ], id="portal-tabs", active_tab=kwargs.get("tab", "anag")),

        html.Div(["Per correzioni ai dati anagrafici o domande sui referti contatta la struttura: ",
                  html.B(FACILITY_PHONE), ". I referti pubblicati sono validati dal medico; "
                  "per l'interpretazione rivolgiti sempre al tuo specialista."],
                 style={"fontSize": "12px", "color": "#6B7280", "marginTop": "26px",
                        "borderTop": "1px solid #E5E7EB", "paddingTop": "14px"}),
    ], className="portal-shell")


# ── Anagrafica ────────────────────────────────────────────────────────────────
def _tab_profile(p):
    consent_date = p["consent_privacy_at"].strftime("%d/%m/%Y") if p["consent_privacy_at"] else "—"
    return html.Div([
        html.H5("Dati anagrafici", className="mt-3 mb-2"),
        dbc.Row([_field("Nome", p["first_name"]), _field("Cognome", p["last_name"]),
                 _field("Codice fiscale", p["fiscal_code"]),
                 _field("Data di nascita", "/".join(reversed(p["birth_date"].split("-"))) if p["birth_date"] else ""),
                 _field("Luogo di nascita", p["birth_place"]), _field("Sesso", p["gender"]),
                 _field("Nazionalità", p["nazionalita"]), _field("Gruppo sanguigno", p["blood"]),
                 _field("Codice paziente", p["code"])], className="g-2"),
        html.H5("Contatti", className="mt-3 mb-2"),
        dbc.Row([_field("Email", p["email"]), _field("Telefono", p["phone"]),
                 _field("Indirizzo", p["address"])], className="g-2"),
        html.H5("Parametri antropometrici", className="mt-3 mb-2"),
        dbc.Row([_field("Peso", f"{p['peso']} kg" if p["peso"] else ""),
                 _field("Altezza", f"{p['altezza']} cm" if p["altezza"] else ""),
                 _field("BMI", p["bmi"])], className="g-2"),
        html.H5("Privacy e comunicazioni", className="mt-3 mb-2"),
        html.Div([
            dbc.Switch(id="portal-consent-email", value=p["consent_email"],
                       label="Ricevi conferme e promemoria degli appuntamenti via email"),
            html.Div(id="portal-consent-msg", style={"fontSize": "12px", "color": "#059669"}),
            html.Div(f"Informativa privacy accettata il {consent_date}. "
                     f"Accesso tramite {'provider ' + p['auth_provider'].title() if p['auth_provider'] else 'email e password'}.",
                     style={"fontSize": "12px", "color": "#6B7280", "marginTop": "6px"}),
        ], className="field-card"),
    ])


@callback(Output("portal-consent-msg", "children"), Input("portal-consent-email", "value"),
          prevent_initial_call=True)
def update_consent(value):
    me = current_patient()
    if not me:
        return dash.no_update
    portal_db.set_email_consent(me[0], bool(value))
    audit("consent_email_changed", "patient", me[0], detail=str(bool(value)))
    return "Preferenza salvata." if value else "Non riceverai più email sugli appuntamenti."


# ── Cartella clinica ──────────────────────────────────────────────────────────
def _lab_table(results):
    if not results:
        return html.Div()
    return html.Table([
        html.Thead(html.Tr([html.Th("Esame"), html.Th("Risultato"), html.Th("Unità"),
                            html.Th("Valori di riferimento"), html.Th("")])),
        html.Tbody([html.Tr([
            html.Td(r["analyte"]),
            html.Td(r["value"], className=f"flag-{r['flag']}"),
            html.Td(r["unit"]), html.Td(r["ref_range"]),
            html.Td({"H": "▲ alto", "L": "▼ basso"}.get(r["flag"], ""), className=f"flag-{r['flag']}"),
        ]) for r in results]),
    ], className="lab-table")


def _doc_accordion(docs):
    if not docs:
        return dbc.Alert("Nessun referto per il filtro selezionato.", color="light")
    items = []
    for d in docs:
        title = html.Div([html.Span(d["category_label"], className=f"cat-pill cat-{d['category']}"),
                          html.B(d["title"]),
                          html.Span(f"  ·  {to_local(d['issued_at']):%d/%m/%Y}", className="doc-meta")])
        items.append(dbc.AccordionItem([
            html.Div(f"{d['author']}  ·  {d['department']}"
                     + ("  ·  referto aggiornato" if d["status"] == "amended" else ""),
                     className="doc-meta mb-2"),
            html.Div(d["body"], className="doc-body"),
            _lab_table(d["results"]),
        ], title=title, item_id=f"doc-{d['id']}"))
    return dbc.Accordion(items, start_collapsed=True, always_open=True)


def _tab_documents(docs):
    if not docs:
        return html.Div(dbc.Alert("Non ci sono ancora referti disponibili.", color="light"), className="mt-3")
    return html.Div([
        html.Div([html.Span("Filtra per tipo: ", style={"fontSize": "13px"}),
                  dcc.Dropdown(id="portal-doc-filter",
                               options=[{"label": "Tutti", "value": "ALL"}] +
                                       [{"label": portal_db.CATEGORY_LABEL[c], "value": c}
                                        for c in sorted({d["category"] for d in docs})],
                               value="ALL", clearable=False, style={"width": "260px", "fontSize": "13px"})],
                 style={"display": "flex", "alignItems": "center", "gap": "10px", "margin": "16px 0 12px"}),
        html.Div(_doc_accordion(docs), id="portal-doc-list"),
    ])


@callback(Output("portal-doc-list", "children"), Input("portal-doc-filter", "value"),
          prevent_initial_call=True)
def filter_docs(cat):
    me = current_patient()
    if not me:
        return dash.no_update
    docs = portal_db.documents(me[1])
    if cat and cat != "ALL":
        docs = [d for d in docs if d["category"] == cat]
    audit("documents_view", "patient", me[0], resource="documents", detail=cat)
    return _doc_accordion(docs)


# ── Appuntamenti ──────────────────────────────────────────────────────────────
def _appt_card(a, show_ics=True):
    d = to_local(a["start_at"])
    extra = []
    if a["instructions"]:
        extra.append(html.Div(["ℹ️  ", a["instructions"]], className="appt-instr"))
    actions = []
    if show_ics and a["status"] == "booked":
        actions.append(html.A("📆  Aggiungi al calendario",
                              href=f"/portal-files/appointment/{a['id']}.ics",
                              style={"fontSize": "12px", "fontWeight": "600", "color": "#D63384"}))
    return html.Div([
        html.Div([html.Div(d.day, className="d"), html.Div(MESI[d.month - 1][:3], className="m"),
                  html.Div(d.year, style={"fontSize": "10px", "color": "#6B7280"})], className="appt-date"),
        html.Div([
            html.Div([html.Span(a["type"], className="appt-title"),
                      html.Span(a["status_label"], className=f"badge-status st-{a['status']}",
                                style={"marginLeft": "10px"})]),
            html.Div(f"🕘 {fmt_long(a['start_at'])}  ·  {a['duration_min']} min", className="appt-info"),
            html.Div(f"📍 {a['location']}" + (f"  ·  👩‍⚕️ {a['clinician']}" if a["clinician"] else ""),
                     className="appt-info"),
            *extra,
            html.Div(actions, style={"marginTop": "8px"}),
        ], style={"flex": "1"}),
    ], className="appt-card", style={} if a["status"] == "booked" else {"borderLeftColor": "#D1D5DB"})


def _tab_appointments(appts):
    now = utcnow()
    upcoming = sorted([a for a in appts if a["start_at"] >= now and a["status"] == "booked"],
                      key=lambda a: a["start_at"])
    history = [a for a in appts if a not in upcoming]
    return html.Div([
        html.H5("Prossimi appuntamenti", className="mt-3 mb-3"),
        *([_appt_card(a) for a in upcoming] or
          [dbc.Alert("Nessun appuntamento in programma.", color="light")]),
        html.Div(f"Per disdire o spostare un appuntamento chiama il {FACILITY_PHONE} "
                 "con almeno 48 ore di anticipo.", style={"fontSize": "12px", "color": "#6B7280"}),
        html.H5("Storico", className="mt-4 mb-3"),
        *([_appt_card(a, show_ics=False) for a in history] or
          [html.Div("Nessun appuntamento passato.", style={"color": "#9CA3AF", "fontSize": "13px"})]),
    ])
