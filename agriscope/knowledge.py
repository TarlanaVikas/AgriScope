"""Plain-language reference notes for each class the shipped weights can predict.

This is *static, general* agronomy guidance written to help a reader interpret a detection.
It is NOT produced by the model, is not a diagnosis, and does not include product names or
doses (those depend on crop, region and regulation: ask a local extension service).
Entries are keyed by the class name stored in the weights, normalised by `_key()`.
"""
from __future__ import annotations

import re

GROUPS = {
    "fungal": "Fungal and mold-type disease",
    "bacterial": "Bacterial disease",
    "viral": "Viral disease",
    "pest": "Insect pest damage",
    "mixed": "Symptom with several possible causes",
    "healthy": "Healthy tissue",
}


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


# key -> (display label, group, summary, signs to look for, general next steps)
_ENTRIES = {
    "aphids": ("Aphids", "pest",
        "Small soft-bodied insects that feed on sap, usually clustered on young shoots and leaf undersides.",
        ["Clusters of tiny green, black or yellow insects", "Curled or distorted new growth", "Sticky honeydew or sooty mold on leaves"],
        ["Inspect leaf undersides and growing tips to confirm the insects are present", "A firm jet of water or insecticidal soap can reduce small infestations", "Protect natural enemies such as ladybirds and lacewings", "Aphids can also spread plant viruses, so watch neighbouring plants for mottling"]),
    "earlyblight": ("Early blight", "fungal",
        "A fungal leaf disease (commonly caused by Alternaria) that usually starts on older, lower leaves.",
        ["Brown spots with concentric, target-like rings", "Yellowing around spots", "Lower leaves dying back first"],
        ["Remove and dispose of heavily affected leaves", "Water at the base and avoid wetting foliage", "Rotate crops and clear plant debris after harvest", "Ask a local extension service whether a fungicide is warranted for your crop"]),
    "healthyleaf": ("Healthy leaf", "healthy",
        "The model found tissue that resembles the healthy leaves in its training data.",
        ["Even green colour", "No spots, mold, curling or chewing damage"],
        ["A healthy-leaf detection is not a guarantee: early or hidden problems may not be visible in one photo", "Keep monitoring, and photograph several leaves, including undersides, if you're unsure"]),
    "leafcurl": ("Leaf curl", "mixed",
        "Leaf curling is a symptom, not a single disease. Viruses, sap-feeding insects, heat or water stress and herbicide drift can all cause it.",
        ["Leaves rolling or cupping upward or downward", "Thickened, puckered or distorted leaves", "Possible yellowing or stunted growth"],
        ["Check leaf undersides for insects such as aphids or whiteflies", "Review recent weather, watering and any spraying nearby", "If new growth is curled and stunted across many plants, consider a viral cause and seek local advice"]),
    "leafhoppersandjassids": ("Leafhoppers and jassids", "pest",
        "Small, wedge-shaped sap-feeding insects that jump or scuttle sideways when disturbed.",
        ["Pale stippling on leaves", "Yellowing or scorched leaf edges (sometimes called hopperburn)", "Small insects on leaf undersides"],
        ["Inspect undersides in the morning, when insects are less active", "Remove heavily damaged leaves", "Yellow sticky traps can help you monitor numbers", "Some leafhoppers carry plant pathogens, so check nearby plants"]),
    "molds": ("Mold", "fungal",
        "Mold-type fungal growth on leaves, typically favoured by high humidity and poor air movement.",
        ["Fuzzy or velvety patches (grey, olive or white)", "Yellow patches on the upper leaf surface", "Leaves wilting or dropping in humid conditions"],
        ["Improve ventilation and spacing between plants", "Avoid overhead watering and keep foliage dry", "Remove affected leaves and dispose of them away from the crop", "Identify the specific mold with local help, since management depends on the crop"]),
    "mosaicvirus": ("Mosaic virus", "viral",
        "A group of viruses that cause mottled leaves. They spread by insects, contaminated tools and hands, and sometimes seed.",
        ["Light and dark green mottling or mosaic pattern", "Distorted, smaller or crinkled leaves", "Stunted plants and reduced yield"],
        ["There is no cure for infected plants: removing them can protect healthy ones", "Wash hands and disinfect tools between plants", "Control aphids and other vectors", "Use certified virus-free seed and resistant varieties where available", "Confirm with laboratory testing if the decision matters"]),
    "septoria": ("Septoria leaf spot", "fungal",
        "A fungal leaf spot disease that typically begins on lower leaves and spreads upward in warm, wet weather.",
        ["Many small, round spots with dark borders and pale centres", "Tiny dark specks in the spot centres", "Yellowing and loss of lower leaves"],
        ["Remove affected lower leaves and keep foliage dry", "Mulch to limit soil splash onto leaves", "Rotate crops and clear plant debris after harvest", "Ask a local extension service about protective fungicides"]),
    "bactarialcanker": ("Bacterial canker", "bacterial",
        "A bacterial disease that can cause leaf scorch, wilting and stem lesions. Note: the weights spell this class 'bactarial canker'.",
        ["Browning along leaf margins", "Wilting of leaves or shoots", "Lesions or streaking on stems"],
        ["Isolate and remove severely affected plants", "Disinfect tools and avoid working among wet plants", "Use clean, certified seed or transplants", "Confirm the diagnosis locally: several diseases look similar"]),
    "bacterialspot": ("Bacterial spot", "bacterial",
        "A bacterial leaf disease that spreads in splashing water and warm, humid weather.",
        ["Small, dark, water-soaked spots that may have yellow halos", "Spots that dry and tear, leaving a ragged look", "Leaf drop in severe cases"],
        ["Avoid overhead irrigation and handling wet plants", "Remove and dispose of badly affected leaves", "Use clean seed and rotate crops", "Ask local advisers whether protective sprays suit your crop"]),
    "fleabeetle": ("Flea beetle", "pest",
        "Tiny jumping beetles that chew many small holes in leaves, most damaging to young plants.",
        ["Numerous small 'shot-holes' in leaves", "Tiny dark beetles that jump when disturbed", "Seedlings stunted or wilting"],
        ["Floating row covers protect seedlings", "Keep weeds down and remove crop residue", "Healthy, fast-growing plants tolerate damage better than seedlings do"]),
    "lateblight": ("Late blight", "fungal",
        "A fast-moving disease caused by a water mold (Phytophthora infestans), favoured by cool, wet weather. It can destroy a crop quickly.",
        ["Large, irregular, water-soaked patches that turn brown or black", "White fuzzy growth on leaf undersides in humid weather", "Brown lesions on stems and fruit or tubers"],
        ["Act quickly: late blight spreads between plants and fields", "Remove and bag severely infected plants rather than composting them", "Avoid overhead watering and improve airflow", "Contact a local extension service promptly: control options depend on region"]),
    "leafminer": ("Leafminer", "pest",
        "Larvae of small flies or moths that tunnel inside leaf tissue.",
        ["Winding, pale or silvery tunnels (mines) in leaves", "Small white puncture marks", "Leaves yellowing or dropping in heavy infestations"],
        ["Remove and dispose of leaves with active mines", "Yellow sticky traps help monitor adult flies", "Encourage parasitic wasps and avoid broad-spectrum sprays that harm them"]),
    "powedrymildew": ("Powdery mildew", "fungal",
        "A fungal disease that coats leaves in a white, powdery growth. Unlike many leaf diseases it does not need wet leaves, and it favours humid, shaded conditions. Note: the weights spell this class 'powedry_mildew'.",
        ["White to grey powdery patches on leaf surfaces", "Leaves yellowing, curling or drying", "Reduced vigour on affected plants"],
        ["Improve air circulation and reduce shade", "Avoid excess nitrogen fertiliser, which promotes soft growth", "Remove badly affected leaves", "Ask local advisers about suitable treatments for your crop"]),
    "yellowcurlvirus": ("Yellow curl virus", "viral",
        "A virus (for example tomato yellow leaf curl virus) typically spread by whiteflies. It causes yellowing and upward curling of leaves.",
        ["Yellowing leaf margins with upward curling", "Smaller leaves and stunted plants", "Poor flower and fruit set"],
        ["There is no cure for infected plants: removing them can protect healthy ones", "Control whiteflies with monitoring, traps and barriers", "Use resistant varieties where available", "Confirm with local diagnostic services if needed"]),
}

# Disease-class order used on the website index (matches the weights' training classes).
CLASS_ORDER = ["aphids", "earlyblight", "healthyleaf", "leafcurl", "leafhoppersandjassids", "molds",
               "mosaicvirus", "septoria", "bactarialcanker", "bacterialspot", "fleabeetle", "lateblight",
               "leafminer", "powedrymildew", "yellowcurlvirus"]


def describe_class(raw_name: str) -> dict:
    entry = _ENTRIES.get(_key(raw_name))
    if entry:
        return {"label": entry[0], "group": GROUPS[entry[1]], "group_key": entry[1], "healthy": entry[1] == "healthy"}
    # Unknown class (e.g. someone swapped in new weights): fall back to the raw name, no invented info.
    label = re.sub(r"[_\-]+", " ", raw_name).strip().capitalize() or "Unknown"
    return {"label": label, "group": "Unclassified", "group_key": "unknown", "healthy": False}


def guidance_for(raw_name: str) -> dict | None:
    entry = _ENTRIES.get(_key(raw_name))
    if not entry:
        return None
    return {"summary": entry[2], "signs": entry[3], "actions": entry[4]}


def known_classes() -> list[dict]:
    """Classes for the website index, grouped for display."""
    out = []
    for key in CLASS_ORDER:
        label, group, summary, *_ = _ENTRIES[key]
        out.append({"key": key, "label": label, "group_key": group, "group": GROUPS[group], "summary": summary})
    return out


def grouped_classes() -> list[dict]:
    order = ["fungal", "bacterial", "viral", "pest", "mixed", "healthy"]
    classes = known_classes()
    return [{"key": g, "title": GROUPS[g], "items": [c for c in classes if c["group_key"] == g]} for g in order
            if any(c["group_key"] == g for c in classes)]
