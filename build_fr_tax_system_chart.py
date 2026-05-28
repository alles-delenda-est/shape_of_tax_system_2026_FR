#!/usr/bin/env python3
"""Construit le graphique sunburst du système fiscal français (année 2023).

Architecture : un unique tableau de feuilles (LEAVES) liste chaque
prélèvement obligatoire avec sa valeur 2023 et deux chemins parents — un
pour le format « UK » (catégorisation économique du chart taxpolicy.org.uk)
et un pour le format « FR » (catégorisation par grand agrégat INSEE/D.).
Deux arbres sont construits à partir des mêmes feuilles ; la timeline
ECharts propose 4 vues : (format) × (Md€ | % PIB).

Sources : INSEE Comptes de la Nation 2023, FIPECO, Cour des comptes NEB
2023, DGFiP Statistiques, Sécurité sociale Chiffres clés 2023.
"""
import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# PIB nominal France 2023 (INSEE, Comptes de la Nation 2023), en M€.
GDP_M = 2803000
ROOT_NAME = "Tous prélèvements obligatoires"


# ---------------------------------------------------------------------------
# Feuilles : chaque prélèvement obligatoire est listé une seule fois, avec
# deux chemins parents possibles. La valeur est en millions d'euros (2023).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Leaf:
    name: str
    value_m: float
    uk_path: tuple
    fr_path: tuple
    note: Optional[str] = None


LEAVES = [
    # === Cotisations sociales ===
    Leaf("Cotisations employeurs", 275400,
         uk_path=("Travail", "Cotisations sociales"),
         fr_path=("Cotisations sociales",)),
    Leaf("Cotisations salariés", 102600,
         uk_path=("Travail", "Cotisations sociales"),
         fr_path=("Cotisations sociales",)),
    Leaf("Cotisations indépendants", 25000,
         uk_path=("Travail", "Cotisations sociales"),
         fr_path=("Cotisations sociales",)),
    Leaf("Autres cotisations", 8000,
         uk_path=("Travail", "Cotisations sociales"),
         fr_path=("Cotisations sociales",),
         note="Cotisations prises en charge par l'État, par l'Unédic, par les régimes complémentaires, etc."),

    # === CSG ===
    Leaf("CSG sur l'activité", 100000,
         uk_path=("Travail", "CSG"),
         fr_path=("Impôts sur les revenus", "CSG"),
         note="Estimée d'après la ventilation FIPECO de l'assiette CSG."),
    Leaf("CSG sur revenus de remplacement", 22000,
         uk_path=("Travail", "CSG"),
         fr_path=("Impôts sur les revenus", "CSG"),
         note="Pensions de retraite, allocations chômage, etc."),
    Leaf("CSG sur revenus du capital", 22000,
         uk_path=("Patrimoine", "Prélèvements sociaux sur le capital"),
         fr_path=("Impôts sur les revenus", "CSG")),
    Leaf("CSG sur les jeux", 1000,
         uk_path=("Autres", "Jeux d'argent"),
         fr_path=("Impôts sur les revenus", "CSG")),

    # === CRDS ===
    Leaf("CRDS sur l'activité", 6500,
         uk_path=("Travail", "CRDS"),
         fr_path=("Impôts sur les revenus", "CRDS")),
    Leaf("CRDS sur revenus de remplacement", 1500,
         uk_path=("Travail", "CRDS"),
         fr_path=("Impôts sur les revenus", "CRDS")),
    Leaf("CRDS sur revenus du capital", 1000,
         uk_path=("Patrimoine", "Prélèvements sociaux sur le capital"),
         fr_path=("Impôts sur les revenus", "CRDS")),

    # === Prélèvement de solidarité 7,5 % ===
    Leaf("Prélèvement de solidarité (7,5 %)", 16000,
         uk_path=("Patrimoine", "Prélèvements sociaux sur le capital"),
         fr_path=("Impôts sur les revenus",)),

    # === Impôt sur le revenu ===
    Leaf("Impôt sur le revenu (travail)", 73900,
         uk_path=("Travail",),
         fr_path=("Impôts sur les revenus", "Impôt sur le revenu"),
         note="Part de l'IR net (86,9 Md€) hors revenus du capital, estimée à environ 74 Md€."),
    Leaf("Impôt sur le revenu (capital)", 13000,
         uk_path=("Patrimoine",),
         fr_path=("Impôts sur les revenus", "Impôt sur le revenu"),
         note="Part de l'IR portant sur dividendes, intérêts, plus-values et revenus fonciers — estimée."),

    # === Impôts sur les salaires (D.29A) ===
    Leaf("Taxe sur les salaires", 16000,
         uk_path=("Travail",),
         fr_path=("Impôts sur les salaires",)),
    Leaf("Versement mobilité", 9300,
         uk_path=("Travail",),
         fr_path=("Impôts sur les salaires",)),
    Leaf("Contribution unique formation/apprentissage (CUFPA)", 10000,
         uk_path=("Travail",),
         fr_path=("Impôts sur les salaires",)),
    Leaf("Forfait social", 5500,
         uk_path=("Travail",),
         fr_path=("Impôts sur les salaires",)),
    Leaf("Contribution solidarité autonomie", 3300,
         uk_path=("Travail",),
         fr_path=("Impôts sur les salaires",)),

    # === TVA ===
    Leaf("TVA", 205000,
         uk_path=("Biens et services",),
         fr_path=(),                  # top-level dans le format FR
         note="Recette nette (mesure « prélèvements obligatoires » Eurostat/INSEE). Répartie entre l'État, la Sécurité sociale et les collectivités après affectations."),

    # === Impôts sur les produits hors TVA (D.214) ===
    Leaf("TICPE", 30000,
         uk_path=("Biens et services",),
         fr_path=("Impôts sur les produits hors TVA",),
         note="Taxe intérieure de consommation sur les produits énergétiques — total État + collectivités."),
    Leaf("TSCA", 17000,
         uk_path=("Biens et services",),
         fr_path=("Impôts sur les produits hors TVA",),
         note="Taxe spéciale sur les conventions d'assurances."),
    Leaf("Droits sur les tabacs", 13200,
         uk_path=("Biens et services",),
         fr_path=("Impôts sur les produits hors TVA",)),
    Leaf("Bière et cidre", 760,
         uk_path=("Biens et services", "Droits sur les alcools"),
         fr_path=("Impôts sur les produits hors TVA", "Droits sur les alcools")),
    Leaf("Vins et alcools intermédiaires", 920,
         uk_path=("Biens et services", "Droits sur les alcools"),
         fr_path=("Impôts sur les produits hors TVA", "Droits sur les alcools")),
    Leaf("Spiritueux", 2520,
         uk_path=("Biens et services", "Droits sur les alcools"),
         fr_path=("Impôts sur les produits hors TVA", "Droits sur les alcools")),
    Leaf("Accise sur l'électricité", 1000,
         uk_path=("Biens et services",),
         fr_path=("Impôts sur les produits hors TVA",),
         note="Ex-CSPE, rendement très réduit en 2023 du fait du bouclier tarifaire."),
    Leaf("TICGN (gaz naturel)", 1500,
         uk_path=("Biens et services",),
         fr_path=("Impôts sur les produits hors TVA",)),
    Leaf("Taxe sur les billets d'avion", 500,
         uk_path=("Biens et services",),
         fr_path=("Impôts sur les produits hors TVA",)),
    Leaf("Taxe boissons sucrées", 500,
         uk_path=("Biens et services",),
         fr_path=("Impôts sur les produits hors TVA",)),
    Leaf("Autres accises de consommation", 800,
         uk_path=("Biens et services",),
         fr_path=("Impôts sur les produits hors TVA",)),

    # === Environnement (classé D.214 en INSEE) ===
    Leaf("Quotas CO2 (SEQE-UE)", 2000,
         uk_path=("Environnement",),
         fr_path=("Impôts sur les produits hors TVA",)),
    Leaf("TGAP", 700,
         uk_path=("Environnement",),
         fr_path=("Impôts sur les produits hors TVA",)),
    Leaf("Autres taxes environnementales", 500,
         uk_path=("Environnement",),
         fr_path=("Impôts sur les produits hors TVA",)),

    # === Jeux d'argent ===
    Leaf("Loterie (FDJ)", 3000,
         uk_path=("Autres", "Jeux d'argent"),
         fr_path=("Impôts sur les produits hors TVA", "Jeux d'argent")),
    Leaf("Paris (sportifs, hippiques)", 1700,
         uk_path=("Autres", "Jeux d'argent"),
         fr_path=("Impôts sur les produits hors TVA", "Jeux d'argent")),
    Leaf("Casinos et jeux de cercle", 1300,
         uk_path=("Autres", "Jeux d'argent"),
         fr_path=("Impôts sur les produits hors TVA", "Jeux d'argent")),
    Leaf("Autres prélèvements jeux", 1000,
         uk_path=("Autres", "Jeux d'argent"),
         fr_path=("Impôts sur les produits hors TVA", "Jeux d'argent")),

    # === Droits d'importation hors TVA ===
    Leaf("Octroi de mer", 1500,
         uk_path=("Autres",),
         fr_path=("Droits d'importation hors TVA",),
         note="Taxe perçue dans les DOM ; classée D.214 en INSEE mais regroupée ici avec les droits d'importation pour la lisibilité du format FR."),

    # === Impôts sur les sociétés (placés sous D.51 en INSEE) ===
    Leaf("Impôt sur les sociétés (net)", 56500,
         uk_path=("Entreprises",),
         fr_path=("Impôts sur les revenus",),
         note="Recette nette des remboursements et dégrèvements (DGFiP, 2023)."),
    Leaf("Contributions exceptionnelles IS", 1000,
         uk_path=("Entreprises",),
         fr_path=("Impôts sur les revenus",)),

    # === Impôts divers sur la production (D.29B) ===
    Leaf("CVAE", 9500,
         uk_path=("Entreprises",),
         fr_path=("Impôts divers sur la production",),
         note="Cotisation sur la valeur ajoutée des entreprises ; suppression progressive 2023-2024."),
    Leaf("CFE", 8000,
         uk_path=("Entreprises",),
         fr_path=("Impôts divers sur la production",),
         note="Cotisation foncière des entreprises."),
    Leaf("C3S", 4000,
         uk_path=("Entreprises",),
         fr_path=("Impôts divers sur la production",),
         note="Contribution sociale de solidarité des sociétés."),
    Leaf("IFER", 1500,
         uk_path=("Entreprises",),
         fr_path=("Impôts divers sur la production",),
         note="Imposition forfaitaire sur les entreprises de réseaux."),
    Leaf("Taxe sur les transactions financières", 1900,
         uk_path=("Entreprises",),
         fr_path=("Impôts divers sur la production",)),
    Leaf("Propriétés bâties", 50600,
         uk_path=("Foncier", "Taxe foncière"),
         fr_path=("Impôts divers sur la production", "Taxe foncière")),
    Leaf("Propriétés non bâties", 1100,
         uk_path=("Foncier", "Taxe foncière"),
         fr_path=("Impôts divers sur la production", "Taxe foncière")),
    Leaf("TEOM", 7000,
         uk_path=("Foncier",),
         fr_path=("Impôts divers sur la production",),
         note="Taxe d'enlèvement des ordures ménagères."),
    Leaf("DMTO", 16300,
         uk_path=("Foncier",),
         fr_path=("Impôts divers sur la production",),
         note="Droits de mutation à titre onéreux (immobilier) — part collectivités."),
    Leaf("Taxe d'aménagement", 1400,
         uk_path=("Foncier",),
         fr_path=("Impôts divers sur la production",)),
    Leaf("Redevances et taxes administratives", 3500,
         uk_path=("Autres",),
         fr_path=("Impôts divers sur la production",)),
    Leaf("Autres taxes affectées et droits divers", 33000,
         uk_path=("Autres",),
         fr_path=("Impôts divers sur la production",),
         note="Solde des prélèvements obligatoires non détaillés ailleurs (droits de timbre, taxes affectées diverses, petites contributions). Cf. annexe « voies et moyens » du PLF."),

    # === Impôts en capital (D.91 + D.59 regroupés ici par souci de lisibilité) ===
    Leaf("Successions", 16600,
         uk_path=("Foncier", "DMTG"),
         fr_path=("Impôts en capital", "DMTG")),
    Leaf("Donations", 4300,
         uk_path=("Foncier", "DMTG"),
         fr_path=("Impôts en capital", "DMTG")),
    Leaf("Taxe d'habitation (résidences secondaires)", 3700,
         uk_path=("Foncier",),
         fr_path=("Impôts en capital",),
         note="Suppression progressive sur les résidences principales achevée en 2023."),
    Leaf("Taxe logements vacants", 200,
         uk_path=("Foncier",),
         fr_path=("Impôts en capital",)),
    Leaf("IFI", 1900,
         uk_path=("Patrimoine",),
         fr_path=("Impôts en capital",),
         note="Impôt sur la fortune immobilière : 176 000 foyers, 1,9 Md€ en 2023 (DGFiP)."),
    Leaf("Droits d'enregistrement divers", 2000,
         uk_path=("Patrimoine",),
         fr_path=("Impôts en capital",)),
]


UK_ORDER = [
    "Travail",
    "Biens et services",
    "Entreprises",
    "Foncier",
    "Patrimoine",
    "Environnement",
    "Autres",
]

FR_ORDER = [
    "Cotisations sociales",
    "TVA",
    "Impôts sur les salaires",
    "Impôts sur les produits hors TVA",
    "Impôts sur les revenus",
    "Droits d'importation hors TVA",
    "Impôts divers sur la production",
    "Impôts en capital",
]


# ---------------------------------------------------------------------------
# Construction d'arbre à partir des feuilles.
# ---------------------------------------------------------------------------
def build_tree(leaves, path_attr, top_order):
    """Construit un arbre {name, value, actual_m, gdp_pct, children?} à partir
    de la liste de feuilles, en suivant le chemin parent ``path_attr``.
    L'ordre des nœuds racines est imposé par ``top_order``.
    """
    roots = {}

    def get_or_create_chain(path):
        current = roots
        for name in path:
            if name not in current:
                current[name] = {"name": name, "children": {}}
            elif "children" not in current[name]:
                raise ValueError(f"Conflit nom de feuille/parent : « {name} »")
            current = current[name]["children"]
        return current

    for leaf in leaves:
        path = getattr(leaf, path_attr)
        parent_dict = get_or_create_chain(path)
        if leaf.name in parent_dict:
            raise ValueError(f"Feuille en double : « {leaf.name} » sous {path}")
        entry = {"name": leaf.name, "value_m": leaf.value_m}
        if leaf.note:
            entry["note"] = leaf.note
        parent_dict[leaf.name] = entry

    def to_list(d):
        out = []
        for name, info in d.items():
            if "children" in info:
                child_list = to_list(info["children"])
                value_m = sum(c["actual_m"] for c in child_list)
                node = {
                    "name": name,
                    "value": value_m / 1000,
                    "actual_m": value_m,
                    "gdp_pct": value_m / GDP_M * 100,
                    "children": child_list,
                }
            else:
                node = {
                    "name": name,
                    "value": info["value_m"] / 1000,
                    "actual_m": info["value_m"],
                    "gdp_pct": info["value_m"] / GDP_M * 100,
                }
                if "note" in info:
                    node["note"] = info["note"]
            out.append(node)
        return out

    tree = to_list(roots)
    rank = {name: i for i, name in enumerate(top_order)}
    return sorted(tree, key=lambda n: rank.get(n["name"], 9999))


# ---------------------------------------------------------------------------
# Couleurs et rendu.
# ---------------------------------------------------------------------------
TOP_COLORS_UK = [
    "#006D77",  # Travail
    "#D9480F",  # Biens et services
    "#2B4C7E",  # Entreprises
    "#F59F00",  # Foncier
    "#8E44AD",  # Patrimoine
    "#2B8A3E",  # Environnement
    "#1B6CA8",  # Autres
]

TOP_COLORS_FR = [
    "#006D77",  # Cotisations sociales
    "#D9480F",  # TVA
    "#0A9396",  # Impôts sur les salaires
    "#F59F00",  # Impôts sur les produits hors TVA
    "#2B4C7E",  # Impôts sur les revenus
    "#1B6CA8",  # Droits d'importation hors TVA
    "#2B8A3E",  # Impôts divers sur la production
    "#8E44AD",  # Impôts en capital
]

CHILD_COLORS = {
    # UK
    "Travail": ["#005F73", "#0A9396", "#3FBAC2", "#89D6CF"],
    "Biens et services": ["#C92A2A", "#E8590C", "#F76707", "#FF922B", "#A61E4D", "#C2255C", "#D6336C", "#F06595"],
    "Entreprises": ["#1E3A5F", "#2B4C7E", "#3D6CB9", "#6D8FE8"],
    "Foncier": ["#B7791F", "#D69E2E", "#ECC94B", "#F6E05E"],
    "Patrimoine": ["#5B21B6", "#7B2CBF", "#A855F7", "#C084FC", "#D8B4FE", "#E9D5FF"],
    "Environnement": ["#1B5E20", "#2B8A3E", "#51A353", "#8BC34A"],
    "Autres": ["#0F4C75", "#1B6CA8", "#2D9DE5", "#5FB6EA"],

    # FR top-level
    "Cotisations sociales": ["#005F73", "#0A8E92", "#1FA9AC", "#48BFC4"],
    "Impôts sur les salaires": ["#0A8E92", "#3FBAC2", "#89D6CF", "#BFE9EA"],
    "Impôts sur les produits hors TVA": ["#C92A2A", "#E8590C", "#F76707", "#FF922B", "#A61E4D", "#C2255C", "#D6336C", "#F06595"],
    "Impôts sur les revenus": ["#1E3A5F", "#2B4C7E", "#3D6CB9", "#6D8FE8", "#5B21B6", "#7B2CBF"],
    "Impôts divers sur la production": ["#1B5E20", "#2B8A3E", "#51A353", "#8BC34A", "#B7791F", "#D69E2E"],
    "Impôts en capital": ["#5B21B6", "#7B2CBF", "#A855F7", "#C084FC", "#D8B4FE"],
    "Droits d'importation hors TVA": ["#0F4C75", "#1B6CA8"],

    # Sub-parents communs aux deux formats
    "DMTG": ["#B7791F", "#D69E2E"],
    "Droits sur les alcools": ["#A61E4D", "#D6336C", "#F06595"],
    "Jeux d'argent": ["#0F4C75", "#1B6CA8", "#2D9DE5", "#5FB6EA"],
    "Taxe foncière": ["#B7791F", "#D69E2E"],
    "Prélèvements sociaux sur le capital": ["#5B21B6", "#7B2CBF", "#A855F7"],
    "Impôt sur le revenu": ["#1E3A5F", "#3D6CB9"],
    "CSG": ["#1E3A5F", "#3D6CB9", "#6D8FE8", "#A8C3F2"],
    "CRDS": ["#2B4C7E", "#3D6CB9", "#6D8FE8"],
}

ITEM_COLORS = {
    "TVA": "#D9480F",
    "Cotisations sociales": "#006D77",
    "Impôts sur les salaires": "#0A9396",
    "Impôts sur les produits hors TVA": "#F59F00",
    "Impôts sur les revenus": "#2B4C7E",
    "Droits d'importation hors TVA": "#1B6CA8",
    "Impôts divers sur la production": "#2B8A3E",
    "Impôts en capital": "#8E44AD",
}

ITEM_STYLE_OVERRIDES = {}


LABEL_THRESHOLD_M = 3000
FORCE_LABELS = {
    # UK
    "Travail", "Biens et services", "Entreprises", "Foncier", "Patrimoine",
    "Environnement", "Autres",
    # FR
    "Cotisations sociales", "TVA", "Impôts sur les salaires",
    "Impôts sur les produits hors TVA", "Impôts sur les revenus",
    "Droits d'importation hors TVA", "Impôts divers sur la production",
    "Impôts en capital",
    # Sub-parents notables
    "CSG", "CRDS", "Impôt sur le revenu", "Impôt sur les sociétés (net)",
    "TICPE", "TSCA", "Taxe foncière", "DMTG", "DMTO", "IFI",
    "Droits sur les tabacs", "Quotas CO2 (SEQE-UE)", "Jeux d'argent",
    "Octroi de mer", "TGAP",
}


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


def total_layout_m(data):
    return sum(item["layout_m"] for item in data)


def root_tooltip(data, mode):
    total_m = total_layout_m(data)
    value = format_gdp(total_m) if mode == "gdp" else format_money_whole(total_m)
    return {"formatter": f"{ROOT_NAME}, {value}"}


def build_view(leaves, path_attr, top_order, palette, mode):
    """Construit l'arbre coloré + libellé pour un format et un mode donnés."""
    tree = build_tree(leaves, path_attr, top_order)
    apply_colors(tree, palette)
    apply_layout_values(tree, mode)
    apply_display_labels(tree, mode)
    return tree


# ---------------------------------------------------------------------------
# Construction des 4 vues (UK × FR) × (Md€ × % PIB).
# ---------------------------------------------------------------------------
views = [
    {"label": "UK · Md€", "path": "uk_path", "order": UK_ORDER,
     "palette": TOP_COLORS_UK, "mode": "money"},
    {"label": "UK · % PIB", "path": "uk_path", "order": UK_ORDER,
     "palette": TOP_COLORS_UK, "mode": "gdp"},
    {"label": "FR · Md€", "path": "fr_path", "order": FR_ORDER,
     "palette": TOP_COLORS_FR, "mode": "money"},
    {"label": "FR · % PIB", "path": "fr_path", "order": FR_ORDER,
     "palette": TOP_COLORS_FR, "mode": "gdp"},
]

for v in views:
    v["data"] = build_view(LEAVES, v["path"], v["order"], v["palette"], v["mode"])


def make_series(view):
    series = deepcopy(SERIES_TEMPLATE)
    series["tooltip"] = root_tooltip(view["data"], view["mode"])
    series["data"] = view["data"]
    series["color"] = view["palette"]
    return series


SERIES_TEMPLATE = {
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
        "label": {"fontWeight": "bold"},
    },
    "itemStyle": {"borderWidth": 1.25, "borderColor": "#ffffff"},
    "label": {
        "minAngle": 0,
        "overflow": "truncate",
        "fontFamily": "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        "fontSize": 11,
        "fontWeight": 650,
        "color": "#102033",
        "textBorderColor": "rgba(255,255,255,0.88)",
        "textBorderWidth": 3,
    },
    "levels": [
        {
            "itemStyle": {"color": "transparent", "borderColor": "transparent", "borderWidth": 0},
            "label": {"show": False},
        },
        {
            "r0": "3%", "r": "21%",
            "label": {
                "rotate": 0, "minAngle": 0, "fontSize": 12, "fontWeight": 800,
                "color": "#ffffff",
                "textBorderColor": "rgba(15,23,42,0.35)", "textBorderWidth": 2.5,
            },
            "itemStyle": {"borderWidth": 2},
        },
        {"r0": "21%", "r": "48%",
         "label": {"rotate": "tangential", "minAngle": 0, "fontSize": 12, "fontWeight": 750}},
        {"r0": "48%", "r": "82%",
         "label": {"rotate": "radial", "minAngle": 0, "fontSize": 9, "fontWeight": 650}},
        {"r0": "82%", "r": "97%",
         "label": {"rotate": "radial", "minAngle": 0, "fontSize": 7, "fontWeight": 650}},
        {"r0": "97%", "r": "100%",
         "label": {"rotate": "radial", "minAngle": 0, "fontSize": 6, "fontWeight": 650}},
    ],
}


initial_series = make_series(views[0])

option = {
    "backgroundColor": "#ffffff",
    "color": TOP_COLORS_UK,
    "_tpaSunburstLeafClickParent": True,
    "baseOption": {
        "timeline": {
            "axisType": "category",
            "bottom": 18,
            "right": 18,
            "width": 220,
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
                "borderWidth": 1,
            },
            "itemStyle": {
                "color": "#F8FAFC",
                "borderColor": "#64748B",
                "borderWidth": 1,
            },
            "label": {
                "fontFamily": "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
                "fontSize": 11,
                "fontWeight": 700,
                "color": "#334155",
            },
            "data": [v["label"] for v in views],
        },
        "tooltip": {"trigger": "item"},
        "series": [initial_series],
    },
    "options": [
        {"tooltip": {"trigger": "item"}, "series": [make_series(v)]}
        for v in views
    ],
}


import shutil

json_payload = json.dumps(option, indent=2, ensure_ascii=False)

# Local copy at the repo root (dev: `python3 -m http.server` from here).
out = Path("fr_tax_system_sunburst_2023.json")
out.write_text(json_payload, encoding="utf-8")

# Build artefact for Vercel: same JSON + a copy of index.html in public/.
public_dir = Path("public")
public_dir.mkdir(exist_ok=True)
(public_dir / "fr_tax_system_sunburst_2023.json").write_text(json_payload, encoding="utf-8")
if Path("index.html").exists():
    shutil.copy("index.html", public_dir / "index.html")

for v in views:
    total_m = total_layout_m(v["data"])
    print(f"  {v['label']:14s}  {total_m / 1000:6.1f} Md€   {total_m / GDP_M * 100:5.2f} %  ({len(v['data'])} catégories racine)")
print(f"\n{out}  écrit ({out.stat().st_size // 1024} Ko)")
