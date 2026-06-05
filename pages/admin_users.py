import dash
from dash import html, dcc, callback, Output, Input, State, ALL, ctx
import dash_bootstrap_components as dbc
from database.auth_db import UserRepository, GroupRepository, ROLE_PERMISSIONS

dash.register_page(__name__, path="/admin/users", name="Gestione Utenti")

ROLE_OPTS = [
    {"label":"👑  Amministratore","value":"admin"},
    {"label":"🩺  Clinico",       "value":"clinician"},
    {"label":"👁  Osservatore",   "value":"viewer"},
]
ROLE_COLORS = {"admin":"#DC2626","clinician":"#D63384","viewer":"#6B7280"}
ROLE_LABELS = {"admin":"Admin","clinician":"Clinico","viewer":"Viewer"}


def _perm_chips(role):
    perms = ROLE_PERMISSIONS.get(role, {})
    items = [
        ("Classifica",   perms.get("can_classify",False)),
        ("Modifica paz.",perms.get("can_edit_patients",False)),
        ("Utenti",       perms.get("can_manage_users",False)),
    ]
    return html.Div([
        html.Span([
            html.Span("✓" if v else "✗",
                      className="perm-yes" if v else "perm-no"),
            f"  {label}",
        ], className="perm-chip")
        for label, v in items
    ])


def _user_table():
    users = UserRepository.get_all()
    if not users:
        return html.P("Nessun utente.", style={"color":"#6B7280"})
    rows = [
        html.Tr([
            html.Th(h, style={"background":"#EDE7F6","color":"#4A235A",
                               "fontWeight":"700","fontSize":"11px",
                               "padding":"10px 14px","textTransform":"uppercase"})
            for h in ["Username","Nome","Gruppo","Ruolo","Ultimo accesso","Attivo",""]
        ])
    ] + [
        html.Tr([
            html.Td(u["username"],     style={"fontWeight":"700","padding":"10px 14px"}),
            html.Td(u["display_name"],style={"padding":"10px 14px"}),
            html.Td(u["group_name"],  style={"padding":"10px 14px","color":"#6B7280"}),
            html.Td(html.Span(ROLE_LABELS.get(u["group_role"],"—"),
                              style={"background":ROLE_COLORS.get(u["group_role"],"#ccc")+"22",
                                     "color":ROLE_COLORS.get(u["group_role"],"#666"),
                                     "fontWeight":"700","fontSize":"11px",
                                     "padding":"3px 10px","borderRadius":"20px"}),
                    style={"padding":"10px 14px"}),
            html.Td(u["last_login"],  style={"padding":"10px 14px","color":"#6B7280","fontSize":"12px"}),
            html.Td("✓" if u["is_active"] else "✗",
                    style={"padding":"10px 14px","color":"#059669" if u["is_active"] else "#DC2626",
                           "fontWeight":"700"}),
            html.Td(
                html.Div([
                    dbc.Button("✏", id={"type":"edit-user","id":u["id"]},
                               size="sm", color="light", style={"marginRight":"4px","fontSize":"12px"}),
                    dbc.Button("🗑", id={"type":"del-user","id":u["id"]},
                               size="sm", color="danger", outline=True, style={"fontSize":"12px"}),
                ]), style={"padding":"6px 14px"}
            ),
        ], style={"borderBottom":"1px solid #F3F4F6",
                  "background":"white" if i%2==0 else "#FAFAFA"})
        for i, u in enumerate(users)
    ]
    return html.Table(rows, style={"width":"100%","borderCollapse":"collapse",
                                    "borderRadius":"10px","overflow":"hidden"})


def _group_cards():
    groups = GroupRepository.get_all()
    return dbc.Row([
        dbc.Col(html.Div([
            html.Div([
                html.Div(g["name"], style={"fontWeight":"700","fontSize":"15px"}),
                html.Span(ROLE_LABELS.get(g["role"],"—"),
                          style={"background":ROLE_COLORS.get(g["role"],"#ccc")+"22",
                                 "color":ROLE_COLORS.get(g["role"],"#666"),
                                 "fontWeight":"700","fontSize":"11px",
                                 "padding":"3px 10px","borderRadius":"20px"}),
            ], style={"display":"flex","justifyContent":"space-between",
                      "alignItems":"center","marginBottom":"8px"}),
            html.Div(g.get("description",""), style={"fontSize":"12px","color":"#6B7280","marginBottom":"10px"}),
            _perm_chips(g["role"]),
            html.Hr(style={"margin":"10px 0"}),
            html.Div(f"{g['user_count']} utenti",
                     style={"fontSize":"12px","color":"#9CA3AF"}),
        ], className="card-box"), md=4)
        for g in groups
    ], className="g-3")


layout = html.Div([
    dcc.Location(id="admin-url"),

    html.Div([
        html.Div([
            html.H1("Gestione Utenti & Gruppi", className="page-title"),
            html.P("Amministrazione accessi e permessi", className="page-subtitle"),
        ]),
        dbc.Button("＋  Nuovo Utente", id="btn-new-user", className="btn-pink"),
    ], className="page-topbar"),

    html.Div([
        # ── Gruppi & ruoli ────────────────────────────────────────────────────
        html.Div("👥  Gruppi & Ruoli", className="card-title mb-2"),
        html.Div(id="groups-section", children=_group_cards()),
        html.Div([
            dbc.Button("＋  Nuovo Gruppo", id="btn-new-group",
                       className="btn-outline-purple mt-2 mb-4"),
        ]),

        # ── Utenti ────────────────────────────────────────────────────────────
        html.Div("🔑  Utenti", className="card-title mb-2"),
        html.Div(id="users-section", children=_user_table()),

    ], style={"padding":"20px 24px"}),

    # ── Modal nuovo/modifica utente ───────────────────────────────────────────
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Utente", id="modal-user-title")),
        dbc.ModalBody([
            dcc.Store(id="editing-user-id", data=None),
            dbc.Row([
                dbc.Col([dbc.Label("Username *", className="form-label"),
                         dbc.Input(id="u-username", placeholder="mario.rossi")], md=6),
                dbc.Col([dbc.Label("Nome visualizzato", className="form-label"),
                         dbc.Input(id="u-displayname", placeholder="Dr. Rossi")], md=6),
            ], className="g-2 mb-2"),
            dbc.Row([
                dbc.Col([dbc.Label("Email", className="form-label"),
                         dbc.Input(id="u-email", type="email")], md=6),
                dbc.Col([dbc.Label("Gruppo", className="form-label"),
                         dbc.Select(id="u-group",
                             options=[{"label":g["name"],"value":str(g["id"])}
                                      for g in GroupRepository.get_all()])], md=6),
            ], className="g-2 mb-2"),
            dbc.Row([
                dbc.Col([dbc.Label("Password *", className="form-label"),
                         dbc.Input(id="u-password", type="password",
                                   placeholder="Lascia vuoto per non cambiare")], md=6),
                dbc.Col([dbc.Label("Attivo", className="form-label"),
                         dbc.Select(id="u-active",
                             options=[{"label":"Sì","value":"1"},
                                      {"label":"No","value":"0"}],
                             value="1")], md=6),
            ], className="g-2 mb-2"),
            html.Div(id="user-form-error",
                     style={"color":"#DC2626","fontSize":"13px","marginTop":"8px"}),
        ]),
        dbc.ModalFooter([
            dbc.Button("Annulla", id="btn-user-cancel", className="btn-outline-purple"),
            dbc.Button("💾  Salva", id="btn-user-save", className="btn-pink"),
        ]),
    ], id="modal-user", is_open=False),

    # ── Modal nuovo gruppo ────────────────────────────────────────────────────
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Nuovo Gruppo")),
        dbc.ModalBody([
            dbc.Label("Nome gruppo *", className="form-label"),
            dbc.Input(id="g-name", placeholder="es. Radiologi", className="mb-2"),
            dbc.Label("Ruolo *", className="form-label"),
            dbc.Select(id="g-role", options=ROLE_OPTS, value="viewer", className="mb-2"),
            dbc.Label("Descrizione", className="form-label"),
            dbc.Input(id="g-desc", placeholder="Descrizione opzionale"),
            html.Div(id="group-form-error",
                     style={"color":"#DC2626","fontSize":"13px","marginTop":"8px"}),
        ]),
        dbc.ModalFooter([
            dbc.Button("Annulla", id="btn-group-cancel", className="btn-outline-purple"),
            dbc.Button("💾  Crea Gruppo", id="btn-group-save", className="btn-pink"),
        ]),
    ], id="modal-group", is_open=False),

    dcc.Store(id="admin-refresh-store"),
])


@callback(
    Output("users-section","children"),
    Output("groups-section","children"),
    Input("admin-refresh-store","data"),
)
def refresh_tables(_):
    return _user_table(), _group_cards()


# ── Modal utente open/close ───────────────────────────────────────────────────
@callback(
    Output("modal-user","is_open"),
    Output("modal-user-title","children"),
    Output("editing-user-id","data"),
    Output("u-username","value"), Output("u-displayname","value"),
    Output("u-email","value"),    Output("u-active","value"),
    Input("btn-new-user","n_clicks"),
    Input("btn-user-cancel","n_clicks"),
    Input("btn-user-save","n_clicks"),
    Input({"type":"edit-user","id":ALL},"n_clicks"),
    prevent_initial_call=True,
)
def toggle_user_modal(n_new, n_cancel, n_save, n_edits):
    blank = (False,"Utente",None,"","","","1")
    tid   = ctx.triggered_id
    if tid in ("btn-user-cancel","btn-user-save") or n_save:
        return blank
    if tid == "btn-new-user":
        return (True,"Nuovo Utente",None,"","","","1")
    if isinstance(tid, dict) and tid.get("type")=="edit-user":
        uid = tid["id"]
        u   = UserRepository.get_by_id(uid)
        if u:
            return (True, f"Modifica — {u['username']}", uid,
                    u["username"], u["display_name"], u["email"],
                    "1" if u["is_active"] else "0")
    return blank


@callback(
    Output("admin-refresh-store","data"),
    Output("user-form-error","children"),
    Input("btn-user-save","n_clicks"),
    State("editing-user-id","data"),
    State("u-username","value"), State("u-displayname","value"),
    State("u-email","value"),    State("u-group","value"),
    State("u-password","value"), State("u-active","value"),
    prevent_initial_call=True,
)
def save_user(n, uid, username, display, email, group_id, password, active):
    if not n: return dash.no_update, ""
    if not username:
        return dash.no_update, "Username obbligatorio."
    try:
        data = {"display_name":display or username, "email":email or "",
                "group_id": int(group_id) if group_id else None,
                "is_active": active == "1"}
        if password: data["password"] = password
        if uid:
            UserRepository.update(int(uid), data)
        else:
            if not password:
                return dash.no_update, "Password obbligatoria per nuovo utente."
            UserRepository.create(username.strip().lower(), password,
                                  display or username, email or "",
                                  int(group_id) if group_id else None)
        return str(n), ""
    except Exception as e:
        return dash.no_update, f"Errore: {e}"


@callback(
    Output("admin-refresh-store","data","allow_duplicate"),
    Input({"type":"del-user","id":ALL},"n_clicks"),
    prevent_initial_call=True,
)
def delete_user(n_clicks):
    tid = ctx.triggered_id
    if isinstance(tid, dict) and any(n_clicks):
        UserRepository.delete(tid["id"])
    return "deleted"


# ── Modal gruppo ──────────────────────────────────────────────────────────────
@callback(
    Output("modal-group","is_open"),
    Input("btn-new-group","n_clicks"),
    Input("btn-group-cancel","n_clicks"),
    Input("btn-group-save","n_clicks"),
    prevent_initial_call=True,
)
def toggle_group_modal(n_new, n_cancel, n_save):
    tid = ctx.triggered_id
    return tid == "btn-new-group"


@callback(
    Output("admin-refresh-store","data","allow_duplicate"),
    Output("group-form-error","children"),
    Input("btn-group-save","n_clicks"),
    State("g-name","value"), State("g-role","value"), State("g-desc","value"),
    prevent_initial_call=True,
)
def save_group(n, name, role, desc):
    if not n: return dash.no_update, ""
    if not name: return dash.no_update, "Nome gruppo obbligatorio."
    try:
        GroupRepository.create(name, role or "viewer", desc or "")
        return str(n), ""
    except Exception as e:
        return dash.no_update, f"Errore: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# GESTIONE PIN PAZIENTI
# ═══════════════════════════════════════════════════════════════════════════════
import dash
from dash import html, dcc, callback, Output, Input, State, ALL, ctx
import dash_bootstrap_components as dbc
from database.auth_db import PatientAuthRepository, generate_pin

# La pagina admin_users già registrata — aggiungiamo una sotto-sezione
# accessibile via /admin/pins

def pin_management_section():
    patients = PatientAuthRepository.get_all_with_pin_status()
    rows = [
        html.Tr([
            html.Th(h, style={"background":"#EDE7F6","color":"#4A235A",
                               "fontWeight":"700","fontSize":"11px",
                               "padding":"10px 14px"})
            for h in ["Codice","Iniziali","PIN attivo","Azione"]
        ])
    ] + [
        html.Tr([
            html.Td(p["code"],     style={"padding":"10px 14px","fontWeight":"700"}),
            html.Td(p["initials"], style={"padding":"10px 14px","color":"#6B7280"}),
            html.Td(
                html.Span("✓ Attivo" if p["has_pin"] else "✗ Non impostato",
                          style={"color":"#059669" if p["has_pin"] else "#DC2626",
                                 "fontWeight":"700","fontSize":"12px"}),
                style={"padding":"10px 14px"}
            ),
            html.Td(
                dbc.Button("🔑  Genera PIN",
                           id={"type":"gen-pin","id":p["id"]},
                           size="sm", className="btn-outline-purple"),
                style={"padding":"6px 14px"}
            ),
        ], style={"borderBottom":"1px solid #F3F4F6",
                  "background":"white" if i%2==0 else "#FAFAFA"})
        for i,p in enumerate(patients)
    ]
    return html.Table(rows, style={"width":"100%","borderCollapse":"collapse",
                                    "borderRadius":"10px","overflow":"hidden"})


@callback(
    Output("pin-result","children"),
    Input({"type":"gen-pin","id":ALL},"n_clicks"),
    prevent_initial_call=True,
)
def gen_pin(n_clicks):
    tid = ctx.triggered_id
    if not isinstance(tid, dict) or not any(n_clicks):
        return dash.no_update
    pid = tid["id"]
    pin = generate_pin()
    PatientAuthRepository.set_pin(pid, pin)
    patients = PatientAuthRepository.get_all_with_pin_status()
    code = next((p["code"] for p in patients if p["id"]==pid), "?")
    return dbc.Alert([
        html.Strong(f"PIN generato per {code}: "),
        html.Code(pin, style={"fontSize":"20px","letterSpacing":"4px",
                              "padding":"2px 10px","background":"#F4F6F9",
                              "borderRadius":"6px"}),
        html.Br(),
        html.Small("Comunica questo PIN al paziente. Non verrà mostrato di nuovo.",
                   style={"color":"#6B7280"}),
    ], color="success", style={"marginTop":"12px"})
