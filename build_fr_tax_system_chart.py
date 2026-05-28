#!/usr/bin/env python3
"""Construit le graphique sunburst du système fiscal français (année 2023).

Adaptation française du build_tax_system_chart.py (UK 2024-25).
Sources principales : INSEE (Comptes de la Nation 2023), FIPECO (synthèses
prélèvements obligatoires), Cour des comptes (NEB 2023 recettes fiscales),
DGFiP Statistiques, Securité sociale (Chiffres clés 2023).

Les montants sont en millions d'euros. Le dénominateur PIB est le PIB nominal
2023 publié par l'INSEE. Quand un poste est estimé (clé de répartition entre
travail/capital pour l'IR, ventilation de la CSG par assiette, etc.) c'est
explicité dans la note du nœud.
"""
import json
from copy import deepcopy
from pathlib import Path

# PIB nominal France 2023 (INSEE, Comptes de la Nation 2023), en M€.
GDP_M = 2803000
ROOT_NAME = "Tous prélèvements obligatoires"

# ----------------------------------------------------------------------------
# Cotisations sociales — total net des allègements ≈ 411 Md€ (FIPECO, 2023).
# Ventilation : ~67 % employeurs / 33 % ménages (FIPECO), répartie sur la base
# des assiettes connues (salariés privés, fonctionnaires, indépendants).
# ----------------------------------------------------------------------------
COTISATIONS_TOTAL = 411000
COTISATIONS_EMPLOYEURS = 275400          # ≈ 67 % de 411 Md€
COTISATIONS_SALARIES = 102600            # part « salariés » du secteur privé + public
COTISATIONS_INDEPENDANTS = 25000         # cotisations des travailleurs non salariés
COTISATIONS_AUTRES = (
    COTISATIONS_TOTAL
    - COTISATIONS_EMPLOYEURS
    - COTISATIONS_SALARIES
    - COTISATIONS_INDEPENDANTS
)  # cotisations diverses (chômeurs, inactifs, prises en charge par l'État)

# ----------------------------------------------------------------------------
# CSG : ~145 Md€ en 2023 (1 point ≈ 16,9 Md€, taux moyen ~8,6 points sur
# l'ensemble des assiettes). Ventilation par assiette d'après la structure
# FIPECO.
# ----------------------------------------------------------------------------
CSG_TOTAL = 145000
CSG_ACTIVITE = 100000           # revenus d'activité (salaires + indépendants)
CSG_REMPLACEMENT = 22000        # pensions de retraite, allocations chômage, etc.
CSG_CAPITAL = 22000             # revenus du patrimoine et placements
CSG_JEUX = CSG_TOTAL - CSG_ACTIVITE - CSG_REMPLACEMENT - CSG_CAPITAL  # ≈ 1 Md€

# CRDS : taux unique 0,5 %. Recette annuelle ~9 Md€ (Cades).
CRDS_TOTAL = 9000
CRDS_ACTIVITE = 6500
CRDS_REMPLACEMENT = 1500
CRDS_CAPITAL = CRDS_TOTAL - CRDS_ACTIVITE - CRDS_REMPLACEMENT

# Prélèvement de solidarité 7,5 % sur revenus du capital
PS_SOLIDARITE_CAPITAL = 16000

# ----------------------------------------------------------------------------
# Impôt sur le revenu (IR net) : 86,9 Md€ en 2023 (DGFiP).
# Estimation de la part « capital » (dividendes, intérêts au barème, plus-values
# au barème, revenus fonciers) à ~13 Md€ ; le reste est rattaché aux revenus
# du travail et de remplacement.
# ----------------------------------------------------------------------------
IR_TOTAL = 86900
IR_CAPITAL = 13000              # divers revenus du patrimoine soumis au barème ou PFU
IR_TRAVAIL = IR_TOTAL - IR_CAPITAL

# ----------------------------------------------------------------------------
# TVA : on retient la recette nette retenue dans la mesure « prélèvements
# obligatoires » de l'INSEE (≈ 205 Md€ en 2023), répartie entre État,
# Sécurité sociale et collectivités après affectations.
# ----------------------------------------------------------------------------
TVA_NETTE = 205000

# ----------------------------------------------------------------------------
# TICPE : recette totale ~30 Md€ en 2023 (État ~16,8 Md€, transfert aux
# collectivités le reste).
# ----------------------------------------------------------------------------
TICPE_TOTAL = 30000

# Taxes locales / foncier — taxe foncière sur les propriétés bâties : recette
# 2023 environ 50,6 Md€ (toutes collectivités, hors TEOM annexée).
TAXE_FONCIERE_BATIE = 50600
TAXE_FONCIERE_NON_BATIE = 1100
TAXE_HABITATION_RS = 3700        # résidences secondaires (suppression résidences principales)
TEOM = 7000                      # taxe d'enlèvement des ordures ménagères
TAXE_AMENAGEMENT = 1400
TAXE_LOG_VACANTS = 200

# Droits de mutation
DMTO = 16300                     # droits de mutation à titre onéreux (immobilier)
DMTG_SUCCESSIONS = 16600
DMTG_DONATIONS = 4300

# Impôt sur les sociétés et fiscalité des entreprises
IS_NET = 56500
CVAE = 9500                      # encore présente en 2023 (suppression progressive 2023-2024)
CFE = 8000
C3S = 4000
IFER = 1500
TTF = 1900
SURTAXE_IS = 1000                # contributions exceptionnelles / surtaxes sur l'IS

# Patrimoine / placements
IFI = 1900
DROITS_ENREGISTREMENT_AUTRES = 2000

# Consommation spécifique
TABACS = 13200
ALCOOLS = 4200
TSCA = 17000                     # taxe spéciale sur les conventions d'assurances (recette totale)
ACCISE_ELECTRICITE = 1000        # rendement très réduit en 2023 (bouclier tarifaire)
TICGN = 1500                     # accise gaz naturel
BOISSONS_SUCREES = 500
TSBA_AVION = 500
AUTRES_ACCISES_CONSO = 800

# Travail — taxes assises sur la masse salariale
TAXE_SALAIRES = 16000
VERSEMENT_MOBILITE = 9300
CUFPA = 10000                    # taxe d'apprentissage + contribution formation professionnelle
FORFAIT_SOCIAL = 5500
CSA = 3300                       # contribution solidarité autonomie (0,3 %)

# Environnement
TGAP = 700
QUOTAS_CO2 = 2000
AUTRES_ENV = 500

# Jeux d'argent, redevances et divers
JEUX_TOTAL = 7000                # ensemble des taxes sur les jeux (FDJ, PMU, casinos, en ligne…)
JEUX_LOTERIE = 3000
JEUX_PARIS = 1700
JEUX_CASINO = 1300
JEUX_AUTRES = JEUX_TOTAL - JEUX_LOTERIE - JEUX_PARIS - JEUX_CASINO

OCTROI_DE_MER = 1500
REDEVANCES_DIVERSES = 3500
# Solde résiduel : la France compte plus de 200 taxes affectées et petites
# impositions (taxes sur les transports, sur les communications électroniques,
# contributions diverses, droits de timbre, etc.). Le « voies et moyens » du
# PLF en publie le détail. On agrège ici l'enveloppe non isolée par ailleurs
# pour s'aligner sur le total INSEE/FIPECO 2023 des prélèvements obligatoires.
AUTRES_PETITES_TAXES = 33000


LABEL_THRESHOLD_M = 3000
FORCE_LABELS = {
    "Travail",
    "Biens et services",
    "Entreprises",
    "Foncier",
    "Patrimoine",
    "Environnement",
    "Autres",
    "Cotisations sociales",
    "CSG",
    "CRDS",
    "Impôt sur le revenu",
    "TVA",
    "TICPE",
    "Tabacs",
    "Alcools",
    "TSCA",
    "Impôt sur les sociétés",
    "CVAE",
    "Taxe foncière",
    "DMTG",
    "DMTO",
    "IFI",
    "Quotas CO2",
    "TGAP",
    "Jeux d'argent",
}

TOP_COLORS = [
    "#006D77",
    "#D9480F",
    "#2B4C7E",
    "#F59F00",
    "#8E44AD",
    "#2B8A3E",
    "#1B6CA8",
]

CHILD_COLORS = {
    "Travail": ["#005F73", "#0A9396", "#3FBAC2", "#89D6CF"],
    "Cotisations sociales": ["#005F73", "#0A8E92", "#1FA9AC", "#48BFC4"],
    "Biens et services": ["#C92A2A", "#E8590C", "#F76707", "#FF922B", "#A61E4D", "#C2255C", "#D6336C", "#F06595"],
    "Entreprises": ["#1E3A5F", "#2B4C7E", "#3D6CB9", "#6D8FE8"],
    "Foncier": ["#B7791F", "#D69E2E", "#ECC94B", "#F6E05E"],
    "DMTG": ["#B7791F", "#D69E2E"],
    "Patrimoine": ["#5B21B6", "#7B2CBF", "#A855F7", "#C084FC", "#D8B4FE", "#E9D5FF"],
    "Impôt sur le revenu (capital)": ["#5B21B6", "#7B2CBF", "#A855F7"],
    "Prélèvements sociaux sur le capital": ["#5B21B6", "#7B2CBF", "#A855F7"],
    "Environnement": ["#1B5E20", "#2B8A3E", "#51A353", "#8BC34A"],
    "Autres": ["#0F4C75", "#1B6CA8", "#2D9DE5", "#5FB6EA"],
    "Jeux d'argent": ["#0F4C75", "#1B6CA8", "#2D9DE5", "#5FB6EA"],
}

ITEM_COLORS = {}
ITEM_STYLE_OVERRIDES = {}


def node(name, value_m, children=None, note=None):
    item = {
        "name": name,
        "value": max(value_m / 1000, 0),
        "actual_m": value_m,
        "gdp_pct": value_m / GDP_M * 100,
    }
    if note:
        item["note"] = note
    if children:
        item["children"] = children
    return item


def label_for_color(color):
    color = color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    if luminance < 0.47:
        return {
            "color": "#FFFFFF",
            "textBorderColor": "rgba(15,23,42,0.42)",
            "textBorderWidth": 2.8,
        }
    return {
        "color": "#172033",
        "textBorderColor": "rgba(255,255,255,0.88)",
        "textBorderWidth": 3,
    }


def format_money(value_m):
    return f"{value_m / 1000:.1f} Md€"


def format_money_whole(value_m):
    return f"{value_m / 1000:,.0f} Md€".replace(",", " ")


def format_gdp(value_m):
    return f"{value_m / GDP_M * 100:.1f} %"


def should_show_label(item):
    if item.get("is_padding"):
        return False
    return item["actual_m"] >= LABEL_THRESHOLD_M or item["name"] in FORCE_LABELS


def pad_terminal_nodes(items, depth=1, max_depth=4):
    for item in items:
        if "children" in item:
            pad_terminal_nodes(item["children"], depth + 1, max_depth)
            continue
        if depth >= max_depth:
            continue
        child = {
            "name": item["name"],
            "value": item["value"],
            "actual_m": item["actual_m"],
            "gdp_pct": item["gdp_pct"],
            "is_padding": True,
            "itemStyle": {
                **item.get("itemStyle", {}),
                "borderWidth": 0.15,
            },
            "label": {"show": False},
        }
        item["children"] = [child]
        pad_terminal_nodes(item["children"], depth + 1, max_depth)
    return items


def label_size(value_m):
    if value_m >= 50000:
        return 11
    if value_m >= 10000:
        return 9
    if value_m >= 3000:
        return 7
    return 6


def apply_colors(items, palette):
    for idx, item in enumerate(items):
        color = ITEM_COLORS.get(item["name"], palette[idx % len(palette)])
        item["itemStyle"] = {"color": color, **ITEM_STYLE_OVERRIDES.get(item["name"], {})}
        item["label"] = label_for_color(color)
        if "children" in item:
            child_palette = CHILD_COLORS.get(item["name"], palette)
            apply_colors(item["children"], child_palette)
    return items


def apply_layout_values(items, mode):
    for item in items:
        child_total_m = 0
        if "children" in item:
            apply_layout_values(item["children"], mode)
            child_total_m = sum(child["layout_m"] for child in item["children"])
        item["layout_m"] = max(item["actual_m"], child_total_m, 0)
        if mode == "gdp":
            item["value"] = item["layout_m"] / GDP_M * 100
        else:
            item["value"] = item["layout_m"] / 1000
    return items


def apply_display_labels(items, mode):
    for item in items:
        label = item.setdefault("label", {})
        value = format_money(item["actual_m"]) if mode == "money" else format_gdp(item["actual_m"])
        if item.get("is_padding"):
            label["show"] = False
        elif should_show_label(item):
            label["show"] = True
            big = item["actual_m"] >= 10000 or item["name"] in FORCE_LABELS
            label["formatter"] = f"{item['name']}\n{value}" if big else item["name"]
            label["fontSize"] = label_size(item["actual_m"])
            label["lineHeight"] = max(label["fontSize"] + 1, 7)
        else:
            label["show"] = False
        item["tooltip"] = {"formatter": f"{item['name']}<br>{value}"}
        if "children" in item:
            apply_display_labels(item["children"], mode)
    return items


# ----------------------------------------------------------------------------
# Construction de l'arbre des prélèvements obligatoires.
# ----------------------------------------------------------------------------
TRAVAIL_TOTAL = (
    COTISATIONS_TOTAL
    + CSG_ACTIVITE + CSG_REMPLACEMENT
    + CRDS_ACTIVITE + CRDS_REMPLACEMENT
    + IR_TRAVAIL
    + TAXE_SALAIRES
    + VERSEMENT_MOBILITE
    + CUFPA
    + FORFAIT_SOCIAL
    + CSA
)

BIENS_TOTAL = (
    TVA_NETTE + TICPE_TOTAL + TABACS + ALCOOLS + TSCA
    + ACCISE_ELECTRICITE + TICGN + BOISSONS_SUCREES + TSBA_AVION + AUTRES_ACCISES_CONSO
)

ENTREPRISES_TOTAL = IS_NET + CVAE + CFE + C3S + IFER + TTF + SURTAXE_IS

FONCIER_TOTAL = (
    TAXE_FONCIERE_BATIE + TAXE_FONCIERE_NON_BATIE + TAXE_HABITATION_RS
    + DMTO + DMTG_SUCCESSIONS + DMTG_DONATIONS
    + TEOM + TAXE_AMENAGEMENT + TAXE_LOG_VACANTS
)

PS_CAPITAL_TOTAL = CSG_CAPITAL + CRDS_CAPITAL + PS_SOLIDARITE_CAPITAL
PATRIMOINE_TOTAL = IR_CAPITAL + PS_CAPITAL_TOTAL + IFI + DROITS_ENREGISTREMENT_AUTRES

ENV_TOTAL = TGAP + QUOTAS_CO2 + AUTRES_ENV

AUTRES_TOTAL = JEUX_TOTAL + OCTROI_DE_MER + REDEVANCES_DIVERSES + AUTRES_PETITES_TAXES + CSG_JEUX


data_m = [
    node("Travail", TRAVAIL_TOTAL, [
        node("Cotisations sociales", COTISATIONS_TOTAL, [
            node("Cotisations employeurs", COTISATIONS_EMPLOYEURS),
            node("Cotisations salariés", COTISATIONS_SALARIES),
            node("Cotisations indépendants", COTISATIONS_INDEPENDANTS),
            node("Autres cotisations", COTISATIONS_AUTRES,
                 note="Cotisations prises en charge par l'État, par l'Unédic, par les régimes complémentaires, etc."),
        ]),
        node("CSG (activité & remplacement)", CSG_ACTIVITE + CSG_REMPLACEMENT, [
            node("CSG sur l'activité", CSG_ACTIVITE,
                 note="Estimée d'après la ventilation FIPECO de l'assiette CSG."),
            node("CSG sur revenus de remplacement", CSG_REMPLACEMENT,
                 note="Pensions de retraite, allocations chômage et autres revenus de remplacement."),
        ]),
        node("CRDS (activité & remplacement)", CRDS_ACTIVITE + CRDS_REMPLACEMENT, [
            node("CRDS sur l'activité", CRDS_ACTIVITE),
            node("CRDS sur revenus de remplacement", CRDS_REMPLACEMENT),
        ]),
        node("Impôt sur le revenu (travail)", IR_TRAVAIL,
             note="Part de l'IR net (86,9 Md€) hors revenus du capital, estimée à environ 74 Md€."),
        node("Taxe sur les salaires", TAXE_SALAIRES),
        node("Versement mobilité", VERSEMENT_MOBILITE),
        node("Contribution unique formation/apprentissage (CUFPA)", CUFPA),
        node("Forfait social", FORFAIT_SOCIAL),
        node("Contribution solidarité autonomie", CSA),
    ]),
    node("Biens et services", BIENS_TOTAL, [
        node("TVA", TVA_NETTE,
             note="Recette nette (mesure « prélèvements obligatoires » Eurostat/INSEE). Répartie entre l'État, la Sécurité sociale et les collectivités après affectations."),
        node("TICPE", TICPE_TOTAL,
             note="Taxe intérieure de consommation sur les produits énergétiques — total État + collectivités."),
        node("Droits sur les tabacs", TABACS),
        node("TSCA", TSCA,
             note="Taxe spéciale sur les conventions d'assurances."),
        node("Droits sur les alcools", ALCOOLS, [
            node("Bière et cidre", int(ALCOOLS * 0.18)),
            node("Vins et alcools intermédiaires", int(ALCOOLS * 0.22)),
            node("Spiritueux", ALCOOLS - int(ALCOOLS * 0.18) - int(ALCOOLS * 0.22)),
        ]),
        node("Accise sur l'électricité", ACCISE_ELECTRICITE,
             note="Ex-CSPE, rendement très réduit en 2023 du fait du bouclier tarifaire."),
        node("TICGN (gaz naturel)", TICGN),
        node("Taxe sur les billets d'avion", TSBA_AVION),
        node("Taxe boissons sucrées", BOISSONS_SUCREES),
        node("Autres accises de consommation", AUTRES_ACCISES_CONSO),
    ]),
    node("Entreprises", ENTREPRISES_TOTAL, [
        node("Impôt sur les sociétés", IS_NET,
             note="Recette nette des remboursements et dégrèvements (DGFiP, 2023)."),
        node("CVAE", CVAE,
             note="Cotisation sur la valeur ajoutée des entreprises ; suppression progressive 2023-2024."),
        node("CFE", CFE,
             note="Cotisation foncière des entreprises."),
        node("C3S", C3S,
             note="Contribution sociale de solidarité des sociétés."),
        node("IFER", IFER,
             note="Imposition forfaitaire sur les entreprises de réseaux."),
        node("Taxe sur les transactions financières", TTF),
        node("Contributions exceptionnelles IS", SURTAXE_IS),
    ]),
    node("Foncier", FONCIER_TOTAL, [
        node("Taxe foncière", TAXE_FONCIERE_BATIE + TAXE_FONCIERE_NON_BATIE, [
            node("Propriétés bâties", TAXE_FONCIERE_BATIE),
            node("Propriétés non bâties", TAXE_FONCIERE_NON_BATIE),
        ]),
        node("Taxe d'habitation (résidences secondaires)", TAXE_HABITATION_RS,
             note="Suppression progressive sur les résidences principales achevée en 2023."),
        node("DMTO", DMTO,
             note="Droits de mutation à titre onéreux (immobilier) — part collectivités."),
        node("DMTG", DMTG_SUCCESSIONS + DMTG_DONATIONS, [
            node("Successions", DMTG_SUCCESSIONS),
            node("Donations", DMTG_DONATIONS),
        ]),
        node("TEOM", TEOM,
             note="Taxe d'enlèvement des ordures ménagères."),
        node("Taxe d'aménagement", TAXE_AMENAGEMENT),
        node("Taxe logements vacants", TAXE_LOG_VACANTS),
    ]),
    node("Patrimoine", PATRIMOINE_TOTAL, [
        node("Impôt sur le revenu (capital)", IR_CAPITAL,
             note="Part de l'IR portant sur dividendes, intérêts, plus-values et revenus fonciers — estimée."),
        node("Prélèvements sociaux sur le capital", PS_CAPITAL_TOTAL, [
            node("CSG sur revenus du capital", CSG_CAPITAL),
            node("CRDS sur revenus du capital", CRDS_CAPITAL),
            node("Prélèvement de solidarité (7,5 %)", PS_SOLIDARITE_CAPITAL),
        ]),
        node("IFI", IFI,
             note="Impôt sur la fortune immobilière : 176 000 foyers, 1,9 Md€ en 2023 (DGFiP)."),
        node("Droits d'enregistrement divers", DROITS_ENREGISTREMENT_AUTRES),
    ]),
    node("Environnement", ENV_TOTAL, [
        node("Quotas CO2 (SEQE-UE)", QUOTAS_CO2),
        node("TGAP", TGAP),
        node("Autres taxes environnementales", AUTRES_ENV),
    ]),
    node("Autres", AUTRES_TOTAL, [
        node("Jeux d'argent", JEUX_TOTAL + CSG_JEUX, [
            node("Loterie (FDJ)", JEUX_LOTERIE),
            node("Paris (sportifs, hippiques)", JEUX_PARIS),
            node("Casinos et jeux de cercle", JEUX_CASINO),
            node("CSG sur les jeux", CSG_JEUX),
            node("Autres prélèvements jeux", JEUX_AUTRES),
        ]),
        node("Octroi de mer", OCTROI_DE_MER),
        node("Redevances et taxes administratives", REDEVANCES_DIVERSES),
        node("Autres taxes affectées et droits divers", AUTRES_PETITES_TAXES,
             note="Solde des prélèvements obligatoires non détaillés ailleurs (droits de timbre, taxes affectées diverses, petites contributions). Cf. annexe « voies et moyens » du PLF."),
    ]),
]

apply_colors(data_m, TOP_COLORS)
apply_layout_values(data_m, "money")
apply_display_labels(data_m, "money")


def convert_to_gdp(data):
    converted = deepcopy(data)
    apply_layout_values(converted, "gdp")
    apply_display_labels(converted, "gdp")
    return converted


def total_layout_m(data):
    return sum(item["layout_m"] for item in data)


def root_tooltip(data, mode):
    total_m = total_layout_m(data)
    value = format_gdp(total_m) if mode == "gdp" else format_money_whole(total_m)
    return {"formatter": f"{ROOT_NAME}, {value}"}


base_series = {
    "name": ROOT_NAME,
    "type": "sunburst",
    "center": ["50%", "50%"],
    "radius": ["0%", "100%"],
    "startAngle": 218,
    "sort": None,
    "nodeClick": "rootToNode",
    "minAngle": 0,
    "labelLayout": {"hideOverlap": True},
    "emphasis": {
        "focus": "ancestor",
        "label": {
            "fontWeight": "bold"
        }
    },
    "itemStyle": {
        "borderWidth": 1.25,
        "borderColor": "#ffffff"
    },
    "label": {
        "minAngle": 0,
        "overflow": "truncate",
        "fontFamily": "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        "fontSize": 11,
        "fontWeight": 650,
        "color": "#102033",
        "textBorderColor": "rgba(255,255,255,0.88)",
        "textBorderWidth": 3
    },
    "levels": [
        {
            "itemStyle": {
                "color": "transparent",
                "borderColor": "transparent",
                "borderWidth": 0
            },
            "label": {"show": False}
        },
        {
            "r0": "3%",
            "r": "21%",
            "label": {
                "rotate": 0,
                "minAngle": 0,
                "fontSize": 12,
                "fontWeight": 800,
                "color": "#ffffff",
                "textBorderColor": "rgba(15,23,42,0.35)",
                "textBorderWidth": 2.5
            },
            "itemStyle": {"borderWidth": 2}
        },
        {
            "r0": "21%",
            "r": "48%",
            "label": {"rotate": "tangential", "minAngle": 0, "fontSize": 12, "fontWeight": 750}
        },
        {
            "r0": "48%",
            "r": "82%",
            "label": {"rotate": "radial", "minAngle": 0, "fontSize": 9, "fontWeight": 650}
        },
        {
            "r0": "82%",
            "r": "97%",
            "label": {"rotate": "radial", "minAngle": 0, "fontSize": 7, "fontWeight": 650}
        },
        {
            "r0": "97%",
            "r": "100%",
            "label": {"rotate": "radial", "minAngle": 0, "fontSize": 6, "fontWeight": 650}
        },
    ],
    "tooltip": root_tooltip(data_m, "money"),
    "data": data_m,
}

option = {
    "backgroundColor": "#ffffff",
    "color": TOP_COLORS,
    "_tpaSunburstLeafClickParent": True,
    "baseOption": {
        "timeline": {
            "axisType": "category",
            "bottom": 18,
            "right": 18,
            "width": 116,
            "height": 28,
            "autoPlay": False,
            "currentIndex": 0,
            "symbolSize": 7,
            "controlStyle": {"show": False},
            "lineStyle": {"color": "#D5DEE8", "width": 2},
            "checkpointStyle": {
                "symbol": "roundRect",
                "symbolSize": 13,
                "color": "#162033",
                "borderColor": "#162033",
                "borderWidth": 1
            },
            "itemStyle": {
                "color": "#F8FAFC",
                "borderColor": "#64748B",
                "borderWidth": 1
            },
            "label": {
                "fontFamily": "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
                "fontSize": 11,
                "fontWeight": 700,
                "color": "#334155"
            },
            "data": ["Md€", "% du PIB"]
        },
        "tooltip": {
            "trigger": "item"
        },
        "series": [base_series],
    },
    "options": [
        {
            "tooltip": {"trigger": "item"},
            "series": [{**base_series, "tooltip": root_tooltip(data_m, "money"), "data": data_m}]
        },
        {
            "tooltip": {"trigger": "item"},
            "series": [{**base_series, "tooltip": root_tooltip(data_m, "gdp"), "data": convert_to_gdp(data_m)}]
        }
    ],
}

out = Path("fr_tax_system_sunburst_2023.json")
out.write_text(json.dumps(option, indent=2, ensure_ascii=False), encoding="utf-8")

total_m = total_layout_m(data_m)
print(f"{out}  —  total {total_m / 1000:,.0f} Md€  ({total_m / GDP_M * 100:.1f} % du PIB)".replace(",", " "))
