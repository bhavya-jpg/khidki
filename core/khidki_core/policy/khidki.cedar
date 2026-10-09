// Khidki safety, school and access policies. Teachers cannot switch these off; only a principal can
// override an activity decision, and every override is logged.

// ── Safety ───────────────────────────────────────────────────────────────────────────────────────
@id("S1")
@en("Outdoor air is severe (PM2.5 above 250). Windows stay shut unless CO₂ reaches 2,000 ppm.")
@hi("बाहर की हवा गंभीर है (PM2.5 250 से ज़्यादा)। CO₂ 2,000 ppm तक न पहुँचे तो खिड़कियाँ बंद रहेंगी।")
forbid (principal, action == Khidki::Action::"ventilate.open", resource)
when { context.outdoorPm25 > 250 && context.co2Band < 4 };

// ── School activities ────────────────────────────────────────────────────────────────────────────
@id("S2")
@en("Outdoor activity moves indoors when forecast PM2.5 during it is above 90 (CPCB 'Poor').")
@hi("गतिविधि के दौरान PM2.5 का पूर्वानुमान 90 से ज़्यादा (CPCB 'ख़राब') हो तो गतिविधि अंदर होगी।")
forbid (principal, action == Khidki::Action::"activity.outdoor", resource)
when { context.maxPm25During > 90 };

@id("S3")
@en("For classes up to V, outdoor activity moves indoors above PM2.5 60.")
@hi("कक्षा V तक के लिए PM2.5 60 से ज़्यादा हो तो बाहर की गतिविधि अंदर होगी।")
forbid (principal, action == Khidki::Action::"activity.outdoor", resource)
when { context.minGrade <= 5 && context.maxPm25During > 60 };

@id("S4")
@en("No outdoor activities at GRAP Stage III or above.")
@hi("GRAP चरण III या उससे ऊपर कोई बाहरी गतिविधि नहीं।")
forbid (principal, action == Khidki::Action::"activity.outdoor", resource)
when { context.grapStage >= 3 };

// ── Defaults ─────────────────────────────────────────────────────────────────────────────────────
@id("P-vent")
@en("Ventilation is allowed unless a safety policy says otherwise.")
@hi("सुरक्षा नीति मना न करे तो खिड़कियाँ खोलना-बंद करना ठीक है।")
permit (
  principal,
  action in [
    Khidki::Action::"ventilate.open",
    Khidki::Action::"ventilate.crack",
    Khidki::Action::"ventilate.close"
  ],
  resource
);

@id("P-act")
@en("Outdoor activities are allowed unless a policy says otherwise.")
@hi("नीति मना न करे तो बाहर की गतिविधियाँ ठीक हैं।")
permit (principal, action == Khidki::Action::"activity.outdoor", resource);

// ── Access ───────────────────────────────────────────────────────────────────────────────────────
@id("A1")
@en("Teachers and parents see their own class.")
@hi("शिक्षक और अभिभावक अपनी कक्षा देख सकते हैं।")
permit (principal, action == Khidki::Action::"view.room", resource)
when { principal in resource };

@id("A2")
@en("The principal sees and manages the whole school.")
@hi("प्रधानाचार्य पूरे स्कूल को देख और संभाल सकते हैं।")
permit (
  principal,
  action in [
    Khidki::Action::"view.room",
    Khidki::Action::"view.school",
    Khidki::Action::"plan.override",
    Khidki::Action::"grap.setOfficial"
  ],
  resource
)
when { principal.role == "principal" && resource in principal.school };

@id("A3")
@en("Only a principal can override a plan or set the official GRAP stage.")
@hi("योजना बदलने या आधिकारिक GRAP चरण तय करने का अधिकार केवल प्रधानाचार्य का है।")
forbid (
  principal,
  action in [Khidki::Action::"plan.override", Khidki::Action::"grap.setOfficial"],
  resource
)
unless { principal.role == "principal" };
