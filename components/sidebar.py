from dash import html

ALL_PAGES = [
    ("/",               "⊞",  "Dashboard",       None),
    ("/patients",       "👥", "Pazienti",         None),
    ("/classification", "🔬", "Classificazione",  "can_classify"),
    ("/statistics",     "📊", "Statistiche",      None),
    ("/xai",            "🧠", "Explainable AI",   None),
    ("/search",         "🔍", "Ricerca Avanzata", None),
    ("/admin/users",    "⚙️", "Utenti & Gruppi", "can_manage_users"),
    ("/admin/pins",     "🔑", "PIN Pazienti",     "can_manage_users"),
]

ROLE_COLORS = {"admin":"#DC2626","clinician":"#D63384","viewer":"#6B7280"}
ROLE_LABELS = {"admin":"Amministratore","clinician":"Clinico","viewer":"Osservatore"}

def sidebar(pathname="/", user=None):
    perms   = user.get("permissions",{}) if user else {}
    allowed = perms.get("pages",["/"])

    sections = {
        "Principale": ["/","/patients","/classification","/statistics"],
        "Analisi": ["/xai","/search"],
        "Amministrazione": ["/admin/users","/admin/pins"],
    }

    nav_blocks = []
    for sec_title, sec_paths in sections.items():
        items = []
        for href, icon, label, perm_key in ALL_PAGES:
            if href not in sec_paths: continue
            if href not in allowed:   continue
            if perm_key and not perms.get(perm_key, False): continue
            is_active = pathname == href
            items.append(html.A(
                [html.Span(icon, style={"fontSize":"15px","minWidth":"20px"}),
                 html.Span(label)],
                href=href,
                className="nav-item-link" + (" active" if is_active else ""),
                style={"gap":"10px"},
            ))
        if items:
            nav_blocks.append(html.Div([
                html.Div(sec_title.upper(),
                         style={"fontSize":"10px","fontWeight":"700","color":"#9CA3AF",
                                "letterSpacing":"1px","padding":"12px 20px 4px"}),
                *items,
            ]))

    if user:
        role     = user.get("role","viewer")
        color    = ROLE_COLORS.get(role,"#6B7280")
        initials = (user.get("display_name","?")[0]).upper()
        user_box = html.Div([
            html.Div(initials, className="user-avatar", style={"background":color}),
            html.Div([
                html.Div(user.get("display_name",""), className="user-name"),
                html.Div(ROLE_LABELS.get(role,role),  className="user-role"),
            ]),
        ], className="user-badge", style={"marginBottom":"6px","cursor":"default"})
        logout = html.A("↩  Esci", href="/logout",
                        style={"fontSize":"12px","color":"#6B7280","display":"block",
                               "textAlign":"center","textDecoration":"none","marginTop":"4px"})
    else:
        user_box = html.Div(); logout = html.Div()

    return html.Div([
        html.Div([
            html.Img(src="/assets/logo.png", style={"width":"155px","marginBottom":"4px"}),
            html.Div("AI Surgical Planning",
                     style={"fontSize":"11px","color":"#9CA3AF","paddingLeft":"4px"}),
        ], style={"padding":"20px 16px 12px"}),
        html.Hr(style={"margin":"0","borderColor":"#E5E7EB"}),
        *nav_blocks,
        html.Div(style={"flexGrow":"1"}),
        html.Hr(style={"margin":"8px 0","borderColor":"#E5E7EB"}),
        html.Div([user_box, logout], style={"padding":"8px 12px 0"}),
        html.Div([
            html.Div("BrCapp  v1.0", className="sidebar-footer-name"),
            html.Div("Uso clinico interno", className="sidebar-footer-sub"),
        ], className="sidebar-footer"),
    ], id="sidebar")
