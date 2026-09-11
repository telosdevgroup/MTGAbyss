"""
necromunda_injuries.py — Official Modern Necromunda Core Rules D66 Lasting Injury Table.
"""

from typing import Dict, Any, Optional

LASTING_INJURIES: Dict[int, Dict[str, Any]] = {
    11: {
        "title": "Lessons Learned",
        "category": "Experience",
        "effect": "The fighter goes Out of Action but learns from their mistakes. They gain +D3 Experience points.",
        "flavor": "A painful brush with death sharpens survival instincts in the underhive.",
        "remedy": "None needed. The fighter is ready for the next battle.",
        "severity": "beneficial",
        "color": 0x22c55e,
        "emoji": "🧠"
    },
    12: {
        "title": "Out Cold",
        "category": "Recovery",
        "effect": "The fighter is knocked unconscious but makes a full recovery. No lasting ill effects.",
        "flavor": "Concussed by flying masonry, the fighter wakes with a throbbing headache and a bruised ego.",
        "remedy": "Cold water and Underhive rotgut. Ready for next battle.",
        "severity": "benign",
        "color": 0x10b981,
        "emoji": "💤"
    },
    13: {
        "title": "Out Cold",
        "category": "Recovery",
        "effect": "The fighter is knocked unconscious but makes a full recovery. No lasting ill effects.",
        "flavor": "Battered against bulkheads, they shake off the ringing in their ears.",
        "remedy": "Full recovery with no lasting penalties.",
        "severity": "benign",
        "color": 0x10b981,
        "emoji": "💤"
    },
    14: {
        "title": "Out Cold",
        "category": "Recovery",
        "effect": "The fighter is knocked unconscious but makes a full recovery. No lasting ill effects.",
        "flavor": "Knocked flat by a heavy blast shockwave; vital organs intact.",
        "remedy": "Full recovery with no lasting penalties.",
        "severity": "benign",
        "color": 0x10b981,
        "emoji": "💤"
    },
    15: {
        "title": "Out Cold",
        "category": "Recovery",
        "effect": "The fighter is knocked unconscious but makes a full recovery. No lasting ill effects.",
        "flavor": "Temporarily incapacitated by toxic fumes or stun charges; lungs cleared by stimm.",
        "remedy": "Full recovery with no lasting penalties.",
        "severity": "benign",
        "color": 0x10b981,
        "emoji": "💤"
    },
    16: {
        "title": "Out Cold",
        "category": "Recovery",
        "effect": "The fighter is knocked unconscious but makes a full recovery. No lasting ill effects.",
        "flavor": "Wakes up hours later in the recovery bunk with zero permanent trauma.",
        "remedy": "Full recovery with no lasting penalties.",
        "severity": "benign",
        "color": 0x10b981,
        "emoji": "💤"
    },
    21: {
        "title": "Grievous Wound",
        "category": "Trauma",
        "effect": "Roll D6: on a 1–3, the fighter suffers a permanent -1 Toughness penalty. On a 4–6, they heal cleanly.",
        "flavor": "Deep shrapnel lacerations or plasma scorch across vital tissue.",
        "remedy": "Visit a Rogue Doc (50 credits) to re-roll traumatic injury results.",
        "severity": "moderate",
        "color": 0xf59e0b,
        "emoji": "🩸"
    },
    22: {
        "title": "Concussion",
        "category": "Characteristic Penalty",
        "effect": "The fighter suffers -1 Willpower and -1 Leadership.",
        "flavor": "A brutal hammer blow rattles cerebral wiring and clouds split-second tactical thinking.",
        "remedy": "Cerebral Stimm-slugs or Lobotomy Bionics at the Black Market.",
        "severity": "moderate",
        "color": 0xf59e0b,
        "emoji": "🌀"
    },
    23: {
        "title": "Eye Injury",
        "category": "Characteristic Penalty",
        "effect": "The fighter suffers -1 Ballistic Skill (BS). If rolled a second time, they are permanently Blinded.",
        "flavor": "A searing las-burn or metal sliver pierces the orbital socket.",
        "remedy": "Bionic Eye (Rare 8, 35 credits) restores full vision and cancels penalty.",
        "severity": "moderate",
        "color": 0xf59e0b,
        "emoji": "👁️"
    },
    24: {
        "title": "Hand Injury",
        "category": "Characteristic Penalty",
        "effect": "The fighter suffers -1 Weapon Skill (WS).",
        "flavor": "Crushed fingers or severed knuckles from a chainsword sweep.",
        "remedy": "Bionic Arm (Rare 9, 45 credits) restores grip and cancels penalty.",
        "severity": "moderate",
        "color": 0xf59e0b,
        "emoji": "🦾"
    },
    25: {
        "title": "Hobbled",
        "category": "Characteristic Penalty",
        "effect": "The fighter suffers -1 Movement (M).",
        "flavor": "A blown-out knee joint or torn Achilles tendon from a high fall.",
        "remedy": "Bionic Leg (Rare 8, 40 credits) or Peg Leg (Trading Post, 10 credits).",
        "severity": "moderate",
        "color": 0xf59e0b,
        "emoji": "🦿"
    },
    26: {
        "title": "Spun Out",
        "category": "Characteristic Penalty",
        "effect": "The fighter suffers -1 Initiative (I).",
        "flavor": "Inner ear equilibrium damage leaving the fighter prone to dizziness and delayed reaction.",
        "remedy": "Stimm-injectors or Chem-synth treatment.",
        "severity": "moderate",
        "color": 0xf59e0b,
        "emoji": "💫"
    },
    31: {
        "title": "Blinded in One Eye",
        "category": "Sensory Trauma",
        "effect": "Suffers -1 Ballistic Skill and cannot re-roll missed hit dice at long range.",
        "flavor": "Permanent loss of depth perception from chemical burns or ricocheting auto-fire.",
        "remedy": "Telescopic Sight or Bionic Eye (Rare 8).",
        "severity": "severe",
        "color": 0xd97706,
        "emoji": "🧿"
    },
    32: {
        "title": "Partially Deafened",
        "category": "Sensory Trauma",
        "effect": "Suffers -1 Cool. Cannot hear incoming stealth charges.",
        "flavor": "Ruptured eardrums from point-blank frag grenade detonations.",
        "remedy": "Bio-scanner or Auspex equipment mitigates sensory loss.",
        "severity": "moderate",
        "color": 0xf59e0b,
        "emoji": "👂"
    },
    33: {
        "title": "Smashed Collarbone",
        "category": "Skeletal Trauma",
        "effect": "Suffers -1 Strength (S).",
        "flavor": "Compound shoulder fracture that never knits properly in cold underhive damp.",
        "remedy": "Goliath Dermal Weave or Servitor Rig wargear.",
        "severity": "severe",
        "color": 0xd97706,
        "emoji": "🦴"
    },
    34: {
        "title": "Broken Arm",
        "category": "Skeletal Trauma",
        "effect": "Suffers -1 Strength and cannot wield two-handed weapons (Heavy Bolter, Grenade Launcher).",
        "flavor": "Mangled limb bound in crude splints; incapable of supporting heavy recoil.",
        "remedy": "Bionic Arm (Rare 9, 45 credits) grants normal two-handed use.",
        "severity": "severe",
        "color": 0xd97706,
        "emoji": "🩹"
    },
    35: {
        "title": "Severed Leg",
        "category": "Mutilation",
        "effect": "Movement characteristic is HALVED. Cannot run or charge until fitted with prosthetic.",
        "flavor": "Limb crushed under collapsed gantry or sheared clean by power weapon.",
        "remedy": "Bionic Leg (Rare 8, 40 credits) or crude Peg Leg (10 credits, allows 2/3 move).",
        "severity": "severe",
        "color": 0xd97706,
        "emoji": "🦿"
    },
    36: {
        "title": "Smashed Flesh",
        "category": "Internal Trauma",
        "effect": "Suffers -1 Toughness (T).",
        "flavor": "Ruptured spleen, cracked ribs, and internal scarring.",
        "remedy": "Hardened Carapace armor or Escher Chem-Alchemy tonic.",
        "severity": "severe",
        "color": 0xd97706,
        "emoji": "💔"
    },
    41: {
        "title": "Horrid Scars",
        "category": "Psychological & Aesthetic",
        "effect": "Gains the Fearsome skill! Enemy fighters must pass a Cool check to declare a charge.",
        "flavor": "Gruesome chemical burns and acid splatter turn the fighter's face into a monstrous visage.",
        "remedy": "Embrace the fear. Use as an intimidation anchor in close combat.",
        "severity": "special",
        "color": 0x8b5cf6,
        "emoji": "👹"
    },
    42: {
        "title": "Bitter Grudge",
        "category": "Psychological & Aesthetic",
        "effect": "Gains Hatred against the opposing gang! Re-rolls all failed melee hit dice against them.",
        "flavor": "Vows vengeance through gritted teeth; burns with a cold, unrelenting underhive vendetta.",
        "remedy": "Hunt down their Leader in the next campaign cycle.",
        "severity": "special",
        "color": 0x8b5cf6,
        "emoji": "🗡️"
    },
    43: {
        "title": "Multiple Injuries",
        "category": "Catastrophic Trauma",
        "effect": "The fighter was caught in a brutal crossfire! Roll twice more on this table.",
        "flavor": "Pinned in the open and riddled with high-caliber rounds.",
        "remedy": "Rogue Doc emergency stabilization mandatory.",
        "severity": "severe",
        "color": 0xd97706,
        "emoji": "💥"
    },
    44: {
        "title": "Multiple Injuries",
        "category": "Catastrophic Trauma",
        "effect": "The fighter was caught in a brutal crossfire! Roll twice more on this table.",
        "flavor": "Blown through railings and pummeled by falling industrial scrap.",
        "remedy": "Rogue Doc emergency stabilization mandatory.",
        "severity": "severe",
        "color": 0xd97706,
        "emoji": "💥"
    },
    45: {
        "title": "Multiple Injuries",
        "category": "Catastrophic Trauma",
        "effect": "The fighter was caught in a brutal crossfire! Roll twice more on this table.",
        "flavor": "Sustained heavy fire from multiple firing lanes.",
        "remedy": "Rogue Doc emergency stabilization mandatory.",
        "severity": "severe",
        "color": 0xd97706,
        "emoji": "💥"
    },
    46: {
        "title": "Multiple Injuries",
        "category": "Catastrophic Trauma",
        "effect": "The fighter was caught in a brutal crossfire! Roll twice more on this table.",
        "flavor": "Crushed beneath a collapsing bulkhead.",
        "remedy": "Rogue Doc emergency stabilization mandatory.",
        "severity": "severe",
        "color": 0xd97706,
        "emoji": "💥"
    },
    51: {
        "title": "Critical Injury",
        "category": "Mortal Threat",
        "effect": "Comatose and bleeding out! Will DIE in post-battle sequence unless treated by a Rogue Doc.",
        "flavor": "Vital fluids draining onto the rusted grating; heartbeat fluttering.",
        "remedy": "Pay 50 credits to consult Rogue Doc or take a Medic check to stabilize.",
        "severity": "fatal_threat",
        "color": 0xef4444,
        "emoji": "🚨"
    },
    52: {
        "title": "Critical Injury",
        "category": "Mortal Threat",
        "effect": "Comatose and bleeding out! Will DIE in post-battle sequence unless treated by a Rogue Doc.",
        "flavor": "Severe internal hemorrhaging; breathing shallow.",
        "remedy": "Emergency Doc visit required to convert to a lasting Flesh Wound.",
        "severity": "fatal_threat",
        "color": 0xef4444,
        "emoji": "🚨"
    },
    53: {
        "title": "Critical Injury",
        "category": "Mortal Threat",
        "effect": "Comatose and bleeding out! Will DIE in post-battle sequence unless treated by a Rogue Doc.",
        "flavor": "Systemic shock from plasma burn or heavy piercing impact.",
        "remedy": "Emergency Doc visit required to save fighter's life.",
        "severity": "fatal_threat",
        "color": 0xef4444,
        "emoji": "🚨"
    },
    54: {
        "title": "Critical Injury",
        "category": "Mortal Threat",
        "effect": "Comatose and bleeding out! Will DIE in post-battle sequence unless treated by a Rogue Doc.",
        "flavor": "Multiple puncture wounds to vital organs.",
        "remedy": "Emergency Doc visit required to save fighter's life.",
        "severity": "fatal_threat",
        "color": 0xef4444,
        "emoji": "🚨"
    },
    55: {
        "title": "Captured!",
        "category": "Capture",
        "effect": "Taken hostage by the opposing gang! Opponent may ransom for credits, sell to Guilders, or trigger a Rescue Mission.",
        "flavor": "Dragged into the shadows while unconscious and stripped of pride.",
        "remedy": "Negotiate ransom credits or declare an immediate Rescue Mission scenario!",
        "severity": "severe",
        "color": 0xa855f7,
        "emoji": "⛓️"
    },
    56: {
        "title": "Captured!",
        "category": "Capture",
        "effect": "Taken hostage by the opposing gang! Opponent may ransom for credits, sell to Guilders, or trigger a Rescue Mission.",
        "flavor": "Handcuffed to an exhaust vent in enemy territory awaiting fate.",
        "remedy": "Negotiate ransom credits or declare an immediate Rescue Mission scenario!",
        "severity": "severe",
        "color": 0xa855f7,
        "emoji": "⛓️"
    },
    61: {
        "title": "Into the Sump",
        "category": "Environmental Hazard",
        "effect": "Fell into toxic chemical runoff! Roll D6: on a 1–2, they die. On a 3–6, they crawl out but lose ALL equipped wargear.",
        "flavor": "Plunges through rotten grates into an emerald vat of bubbling industrial acid.",
        "remedy": "Fighter lives on 3+, but their armor, guns, and gear are dissolved forever.",
        "severity": "fatal_threat",
        "color": 0xef4444,
        "emoji": "☣️"
    },
    62: {
        "title": "Into the Sump",
        "category": "Environmental Hazard",
        "effect": "Fell into toxic chemical runoff! Roll D6: on a 1–2, they die. On a 3–6, they crawl out but lose ALL equipped wargear.",
        "flavor": "Washed downstream into necrotic refinery pipes.",
        "remedy": "Fighter lives on 3+, but gear is lost to the sludge.",
        "severity": "fatal_threat",
        "color": 0xef4444,
        "emoji": "☣️"
    },
    63: {
        "title": "Into the Sump",
        "category": "Environmental Hazard",
        "effect": "Fell into toxic chemical runoff! Roll D6: on a 1–2, they die. On a 3–6, they crawl out but lose ALL equipped wargear.",
        "flavor": "Submerged in promethium effluent and caustic solvents.",
        "remedy": "Fighter lives on 3+, but gear is lost to the sludge.",
        "severity": "fatal_threat",
        "color": 0xef4444,
        "emoji": "☣️"
    },
    64: {
        "title": "Into the Sump",
        "category": "Environmental Hazard",
        "effect": "Fell into toxic chemical runoff! Roll D6: on a 1–2, they die. On a 3–6, they crawl out but lose ALL equipped wargear.",
        "flavor": "Swallowed by toxic slag pools before swimming to safety.",
        "remedy": "Fighter lives on 3+, but gear is lost to the sludge.",
        "severity": "fatal_threat",
        "color": 0xef4444,
        "emoji": "☣️"
    },
    65: {
        "title": "Into the Sump",
        "category": "Environmental Hazard",
        "effect": "Fell into toxic chemical runoff! Roll D6: on a 1–2, they die. On a 3–6, they crawl out but lose ALL equipped wargear.",
        "flavor": "Drags themselves out of the slime coughing black sludge, stripped bare.",
        "remedy": "Fighter lives on 3+, but gear is lost to the sludge.",
        "severity": "fatal_threat",
        "color": 0xef4444,
        "emoji": "☣️"
    },
    66: {
        "title": "Memorable Death",
        "category": "Fatality",
        "effect": "The fighter is slain outright. Cross them off the gang roster permanently. If a friendly fighter was within 3\", wargear may be recovered.",
        "flavor": "A glorious or gruesome demise etched forever into underhive legend.",
        "remedy": "Pour one out at the Drinking Hole. Recruit a fresh Juve to avenge them.",
        "severity": "fatal",
        "color": 0x991b1b,
        "emoji": "☠️"
    }
}

def get_injury(d66: int) -> Optional[Dict[str, Any]]:
    """Retrieves Lasting Injury entry by D66 roll integer (e.g. 23, 66)."""
    return LASTING_INJURIES.get(d66)
