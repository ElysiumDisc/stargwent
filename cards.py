import pygame

class Card:
    """Represents a single card in the game."""

    # Naquadah cost configuration
    NAQUADAH_BASE = 4  # Base cost
    NAQUADAH_HERO_BONUS = 3  # Extra cost for heroes

    def __init__(self, id, name, faction, power, row, ability, image_path=None):
        self.id = id
        self.name = name
        self.faction = faction
        self.power = power
        self.displayed_power = power
        self.row = row # close, ranged, siege, agile
        self.ability = ability
        self.image_path = f"assets/{id}.png"

        # Default sizes (will be updated by reload_card_images)
        self.image = pygame.Surface((80, 120))
        self.hover_image = pygame.Surface((86, 130))
        self.image.fill((80, 80, 90))
        self.hover_image.fill((100, 100, 110))
        self.rect = pygame.Rect(0, 0, 80, 120)

        # Per-play transient flags. Initialised here so calculate_score()
        # paths that read them with `getattr` / `hasattr` can rely on the
        # attribute existing rather than racing the lazy set in play_card().
        # All four are cleared together at round reset in Game._end_round.
        self.hammond_boosted = False
        self.kalel_boosted = False
        self.kiva_boosted = False
        self.adria_boosted = False

    @property
    def naquadah_cost(self) -> int:
        """
        Calculate Naquadah cost based on card power.

        Cost formula:
        - Base: 4 + (power - 1)
        - Heroes (Legendary Commander): +3 bonus

        Power ranges:
        - 1-3 (Common): 4-6 Naquadah
        - 4-6 (Rare): 7-9 Naquadah
        - 7-9 (Epic): 10-12 Naquadah
        - 10+ (Legendary): 13-15 Naquadah
        - Heroes: 13-16+ Naquadah
        """
        base_cost = self.NAQUADAH_BASE + max(0, self.power - 1)

        # Hero bonus
        is_hero = self.ability and "Legendary Commander" in self.ability
        if is_hero:
            base_cost += self.NAQUADAH_HERO_BONUS

        return base_cost

    @property
    def rarity(self) -> str:
        """Get card rarity based on power level."""
        if self.power >= 10:
            return "legendary"
        elif self.power >= 7:
            return "epic"
        elif self.power >= 4:
            return "rare"
        return "common"

    def __repr__(self):
        return f"Card({self.name}, {self.power})"

# Factions
FACTION_TAURI = "Tau'ri"
FACTION_GOAULD = "Goa'uld"
FACTION_JAFFA = "Jaffa Rebellion"
FACTION_LUCIAN = "Lucian Alliance"
FACTION_ASGARD = "Asgard"
FACTION_ALTERAN = "Alteran"
FACTION_NEUTRAL = "Neutral"

# Card Database
ALL_CARDS = {
    # --- Tau'ri ---
    "tauri_oneill": Card("tauri_oneill", "Col. Jack O'Neill", FACTION_TAURI, 10, "close", "Legendary Commander"),
    "tauri_hammond": Card("tauri_hammond", "Gen. George Hammond", FACTION_TAURI, 10, "close", "Legendary Commander"),
    "tauri_jackson": Card("tauri_jackson", "Dr. Daniel Jackson", FACTION_TAURI, 10, "close", "Legendary Commander"),
    "tauri_carter": Card("tauri_carter", "Dr. Samantha Carter", FACTION_TAURI, 10, "ranged", "Legendary Commander"),
    "tauri_sgc_recruit_1": Card("tauri_sgc_recruit_1", "SGC Recruit", FACTION_TAURI, 1, "close", None),
    "tauri_sgc_recruit_2": Card("tauri_sgc_recruit_2", "SGC Recruit", FACTION_TAURI, 1, "close", None),
    "tauri_alpha_team_1": Card("tauri_alpha_team_1", "Alpha Team Troopers", FACTION_TAURI, 1, "close", "Tactical Formation, Gate Reinforcement"),
    "tauri_alpha_team_2": Card("tauri_alpha_team_2", "Alpha Team Troopers", FACTION_TAURI, 1, "close", "Tactical Formation, Gate Reinforcement"),
    "tauri_alpha_team_3": Card("tauri_alpha_team_3", "Alpha Team Troopers", FACTION_TAURI, 1, "close", "Tactical Formation, Gate Reinforcement"),
    "tauri_quinn": Card("tauri_quinn", "Jonas Quinn", FACTION_TAURI, 7, "close", None),
    "tauri_sg1_commando_1": Card("tauri_sg1_commando_1", "SG-1 Commandos", FACTION_TAURI, 4, "close", "Tactical Formation, Gate Reinforcement"),
    "tauri_sg1_commando_2": Card("tauri_sg1_commando_2", "SG-1 Commandos", FACTION_TAURI, 4, "close", "Tactical Formation, Gate Reinforcement"),
    "tauri_sg1_commando_3": Card("tauri_sg1_commando_3", "SG-1 Commandos", FACTION_TAURI, 4, "close", "Tactical Formation, Gate Reinforcement"),
    "tauri_barrett": Card("tauri_barrett", "NID Agent Malcolm Barrett", FACTION_TAURI, 4, "close", "Deep Cover Agent"),
    "tauri_fraiser": Card("tauri_fraiser", "Dr. Janet Fraiser", FACTION_TAURI, 5, "close", "Deep Cover Agent"),
    "tauri_sg3": Card("tauri_sg3", "SG-3 Heavy Recon", FACTION_TAURI, 5, "close", None),
    "tauri_mitchell": Card("tauri_mitchell", "Capt. Cameron Mitchell", FACTION_TAURI, 5, "close", None),
    "tauri_marksman": Card("tauri_marksman", "Airman Marksman", FACTION_TAURI, 4, "ranged", None),
    "tauri_f302_pilot": Card("tauri_f302_pilot", "F-302 Fighter Pilot", FACTION_TAURI, 4, "ranged", None),
    "tauri_tokra_op_1": Card("tauri_tokra_op_1", "Tok'ra Operative", FACTION_TAURI, 5, "ranged", "Tactical Formation"),
    "tauri_tokra_op_2": Card("tauri_tokra_op_2", "Tok'ra Operative", FACTION_TAURI, 5, "ranged", "Tactical Formation"),
    "tauri_tokra_op_3": Card("tauri_tokra_op_3", "Tok'ra Operative", FACTION_TAURI, 5, "ranged", "Tactical Formation"),
    "tauri_vallarin": Card("tauri_vallarin", "Vallarin", FACTION_TAURI, 5, "ranged", None),
    "tauri_vala": Card("tauri_vala", "Liaison Vala Mal Doran", FACTION_TAURI, 5, "ranged", None),
    "tauri_caldwell": Card("tauri_caldwell", "Col. Steven Caldwell", FACTION_TAURI, 6, "ranged", None),
    "tauri_ground_tech_1": Card("tauri_ground_tech_1", "Ground Control Technician", FACTION_TAURI, 1, "siege", "Inspiring Leadership"),
    "tauri_ground_tech_2": Card("tauri_ground_tech_2", "Ground Control Technician", FACTION_TAURI, 1, "siege", "Inspiring Leadership"),
    "tauri_ground_tech_3": Card("tauri_ground_tech_3", "Ground Control Technician", FACTION_TAURI, 1, "siege", "Inspiring Leadership"),
    "tauri_medic_1": Card("tauri_medic_1", "Medical Team (Dr. Lam)", FACTION_TAURI, 5, "siege", "Medical Evac"),
    "tauri_medic_2": Card("tauri_medic_2", "Medical Team (Dr. Lam)", FACTION_TAURI, 5, "siege", "Medical Evac"),
    "tauri_turret_1": Card("tauri_turret_1", "M.A.L.P", FACTION_TAURI, 6, "siege", None),
    "tauri_turret_2": Card("tauri_turret_2", "M.A.L.P", FACTION_TAURI, 6, "siege", None),
    "tauri_turret_3": Card("tauri_turret_3", "M.A.L.P", FACTION_TAURI, 6, "siege", None),
    "tauri_railgun_1": Card("tauri_railgun_1", "Railgun Emplacement", FACTION_TAURI, 6, "siege", None),
    "tauri_railgun_2": Card("tauri_railgun_2", "Railgun Emplacement", FACTION_TAURI, 6, "siege", None),
    "tauri_railgun_3": Card("tauri_railgun_3", "Railgun Emplacement", FACTION_TAURI, 6, "siege", None),
    "tauri_bc304_1": Card("tauri_bc304_1", "BC-304 Heavy Cruiser", FACTION_TAURI, 8, "siege", "Tactical Formation"),
    "tauri_bc304_2": Card("tauri_bc304_2", "BC-304 Heavy Cruiser", FACTION_TAURI, 8, "siege", "Tactical Formation"),
    "tauri_analyst": Card("tauri_analyst", "Analyst", FACTION_TAURI, 1, "siege", "Deep Cover Agent"),
    "tauri_prometheus_1": Card("tauri_prometheus_1", "X-303 Prometheus", FACTION_TAURI, 6, "siege", None),
    "tauri_prometheus_2": Card("tauri_prometheus_2", "X-303 Prometheus", FACTION_TAURI, 6, "siege", None),

    # --- Goa'uld ---
    "goauld_sokar": Card("goauld_sokar", "Sokar", FACTION_GOAULD, 10, "close", "Legendary Commander"),
    "goauld_yu": Card("goauld_yu", "Lord Yu", FACTION_GOAULD, 10, "close", "Legendary Commander"),
    "goauld_hathor": Card("goauld_hathor", "Hathor", FACTION_GOAULD, 8, "ranged", "Legendary Commander, Inspiring Leadership"),
    "goauld_apophis": Card("goauld_apophis", "Apophis", FACTION_GOAULD, 10, "ranged", "Legendary Commander"),
    "goauld_isis": Card("goauld_isis", "Isis", FACTION_GOAULD, 5, "siege", "Legendary Commander"),
    "goauld_unscheduled_jaffa_1": Card("goauld_unscheduled_jaffa_1", "Unscheduled Jaffa", FACTION_GOAULD, 1, "close", "Gate Reinforcement"),
    "goauld_unscheduled_jaffa_2": Card("goauld_unscheduled_jaffa_2", "Unscheduled Jaffa", FACTION_GOAULD, 1, "close", "Gate Reinforcement"),
    "goauld_unscheduled_jaffa_3": Card("goauld_unscheduled_jaffa_3", "Unscheduled Jaffa", FACTION_GOAULD, 1, "close", "Gate Reinforcement"),
    "goauld_drone_1": Card("goauld_drone_1", "Goa'uld Drone", FACTION_GOAULD, 2, "close", "Gate Reinforcement"),
    "goauld_drone_2": Card("goauld_drone_2", "Goa'uld Drone", FACTION_GOAULD, 2, "close", "Gate Reinforcement"),
    "goauld_drone_3": Card("goauld_drone_3", "Goa'uld Drone", FACTION_GOAULD, 2, "close", "Gate Reinforcement"),
    "goauld_serpent_guard_1": Card("goauld_serpent_guard_1", "Serpent Guard Elite", FACTION_GOAULD, 4, "close", "Gate Reinforcement"),
    "goauld_serpent_guard_2": Card("goauld_serpent_guard_2", "Serpent Guard Elite", FACTION_GOAULD, 4, "close", "Gate Reinforcement"),
    "goauld_serpent_guard_3": Card("goauld_serpent_guard_3", "Serpent Guard Elite", FACTION_GOAULD, 4, "close", "Gate Reinforcement"),
    "goauld_kull_warrior_1": Card("goauld_kull_warrior_1", "Kull Warrior", FACTION_GOAULD, 4, "close", "Gate Reinforcement, Life Force Drain"),
    "goauld_kull_warrior_2": Card("goauld_kull_warrior_2", "Kull Warrior", FACTION_GOAULD, 4, "close", "Gate Reinforcement, Life Force Drain"),
    "goauld_osiris_guard_1": Card("goauld_osiris_guard_1", "Osiris Guard", FACTION_GOAULD, 4, "close", "Gate Reinforcement, Life Force Drain"),
    "goauld_osiris_guard_2": Card("goauld_osiris_guard_2", "Osiris Guard", FACTION_GOAULD, 4, "close", "Gate Reinforcement, Life Force Drain"),
    "goauld_horus_guard_1": Card("goauld_horus_guard_1", "Horus Guard", FACTION_GOAULD, 5, "close", "Gate Reinforcement, Life Force Drain"),
    "goauld_horus_guard_2": Card("goauld_horus_guard_2", "Horus Guard", FACTION_GOAULD, 5, "close", "Gate Reinforcement, Life Force Drain"),
    "goauld_anubis_guard_1": Card("goauld_anubis_guard_1", "Anubis Guard", FACTION_GOAULD, 4, "close", "Gate Reinforcement, Life Force Drain"),
    "goauld_anubis_guard_2": Card("goauld_anubis_guard_2", "Anubis Guard", FACTION_GOAULD, 4, "close", "Gate Reinforcement, Life Force Drain"),
    "goauld_bastet_guard_1": Card("goauld_bastet_guard_1", "Bastet Guard", FACTION_GOAULD, 5, "close", "Gate Reinforcement, Life Force Drain"),
    "goauld_bastet_guard_2": Card("goauld_bastet_guard_2", "Bastet Guard", FACTION_GOAULD, 5, "close", "Gate Reinforcement, Life Force Drain"),
    "goauld_council_anubis": Card("goauld_council_anubis", "Council of Anubis", FACTION_GOAULD, 6, "close", "Gate Reinforcement, System Lord's Curse"),
    "goauld_council_baal": Card("goauld_council_baal", "Council of Ba'al", FACTION_GOAULD, 6, "close", "Gate Reinforcement, System Lord's Curse"),
    "goauld_council_yu": Card("goauld_council_yu", "Council of Yu", FACTION_GOAULD, 6, "close", "Gate Reinforcement, System Lord's Curse"),
    "goauld_ashrak": Card("goauld_ashrak", "Ashrak Assassin", FACTION_GOAULD, 6, "close", None),
    "goauld_glider_pilot": Card("goauld_glider_pilot", "Glider Pilot", FACTION_GOAULD, 5, "close", None),
    "goauld_jaffa_master": Card("goauld_jaffa_master", "Jaffa Master", FACTION_GOAULD, 5, "close", None),
    "goauld_rebel_jaffa": Card("goauld_rebel_jaffa", "Captured Rebel Jaffa", FACTION_GOAULD, 5, "close", None),
    "goauld_scout": Card("goauld_scout", "Goa'uld Scout", FACTION_GOAULD, 5, "ranged", "Deep Cover Agent"),
    "goauld_teltak_1": Card("goauld_teltak_1", "Tel'tak Courier", FACTION_GOAULD, 2, "ranged", None),
    "goauld_teltak_2": Card("goauld_teltak_2", "Tel'tak Courier", FACTION_GOAULD, 2, "ranged", None),
    "goauld_teltak_3": Card("goauld_teltak_3", "Tel'tak Courier", FACTION_GOAULD, 2, "ranged", None),
    "goauld_symbiote": Card("goauld_symbiote", "Goa'uld Symbiote", FACTION_GOAULD, 2, "close", None),
    "goauld_lieutenant": Card("goauld_lieutenant", "Goa'uld Lieutenant", FACTION_GOAULD, 2, "ranged", None),
    "goauld_glider_swarm_1": Card("goauld_glider_swarm_1", "Death Glider Swarm", FACTION_GOAULD, 1, "ranged", "Gate Reinforcement"),
    "goauld_glider_swarm_2": Card("goauld_glider_swarm_2", "Death Glider Swarm", FACTION_GOAULD, 1, "ranged", "Gate Reinforcement"),
    "goauld_glider_swarm_3": Card("goauld_glider_swarm_3", "Death Glider Swarm", FACTION_GOAULD, 1, "ranged", "Gate Reinforcement"),
    "goauld_alkesh_1": Card("goauld_alkesh_1", "Al'kesh Bomber", FACTION_GOAULD, 4, "siege", "Gate Reinforcement"),
    "goauld_alkesh_2": Card("goauld_alkesh_2", "Al'kesh Bomber", FACTION_GOAULD, 4, "siege", "Gate Reinforcement"),
    "goauld_alkesh_3": Card("goauld_alkesh_3", "Al'kesh Bomber", FACTION_GOAULD, 4, "siege", "Gate Reinforcement"),
    "goauld_plasma_emplacement": Card("goauld_plasma_emplacement", "Plasma Weapon Emplacement", FACTION_GOAULD, 6, "siege", None),
    "goauld_hatak_1": Card("goauld_hatak_1", "Ha'tak Mothership", FACTION_GOAULD, 6, "siege", "Gate Reinforcement"),
    "goauld_hatak_2": Card("goauld_hatak_2", "Ha'tak Mothership", FACTION_GOAULD, 6, "siege", "Gate Reinforcement"),
    "goauld_ancient_weapon": Card("goauld_ancient_weapon", "Ra Weapon", FACTION_GOAULD, 10, "siege", None),

    # --- Jaffa Rebellion ---
    "jaffa_tealc": Card("jaffa_tealc", "Teal'c", FACTION_JAFFA, 10, "ranged", "Legendary Commander"),
    "jaffa_bratac": Card("jaffa_bratac", "Bra'tac", FACTION_JAFFA, 8, "ranged", "Legendary Commander"),
    "jaffa_raknor": Card("jaffa_raknor", "Rak'nor", FACTION_JAFFA, 5, "close", "Legendary Commander, Inspiring Leadership"),
    "jaffa_master_bratac": Card("jaffa_master_bratac", "Master Bra'tac", FACTION_JAFFA, 10, "close", "Legendary Commander"),
    "jaffa_monk": Card("jaffa_monk", "Jaffa Monk", FACTION_JAFFA, 2, "agile", None),
    "jaffa_defector_1": Card("jaffa_defector_1", "Jaffa Defector", FACTION_JAFFA, 6, "agile", None),
    "jaffa_defector_2": Card("jaffa_defector_2", "Jaffa Defector", FACTION_JAFFA, 6, "agile", None),
    "jaffa_rebel_infantry_1": Card("jaffa_rebel_infantry_1", "Rebel Infantry", FACTION_JAFFA, 6, "agile", None),
    "jaffa_rebel_infantry_2": Card("jaffa_rebel_infantry_2", "Rebel Infantry", FACTION_JAFFA, 6, "agile", None),
    "jaffa_rebel_infantry_3": Card("jaffa_rebel_infantry_3", "Rebel Infantry", FACTION_JAFFA, 6, "agile", None),
    "jaffa_tokra_infiltrator_1": Card("jaffa_tokra_infiltrator_1", "Tok'ra Infiltrator", FACTION_JAFFA, 5, "close", "Gate Reinforcement"),
    "jaffa_tokra_infiltrator_2": Card("jaffa_tokra_infiltrator_2", "Tok'ra Infiltrator", FACTION_JAFFA, 5, "close", "Gate Reinforcement"),
    "jaffa_tokra_infiltrator_3": Card("jaffa_tokra_infiltrator_3", "Tok'ra Infiltrator", FACTION_JAFFA, 5, "close", "Gate Reinforcement"),
    "jaffa_free_jaffa_1": Card("jaffa_free_jaffa_1", "Free Jaffa", FACTION_JAFFA, 5, "close", "Gate Reinforcement"),
    "jaffa_free_jaffa_2": Card("jaffa_free_jaffa_2", "Free Jaffa", FACTION_JAFFA, 5, "close", "Gate Reinforcement"),
    "jaffa_free_jaffa_3": Card("jaffa_free_jaffa_3", "Free Jaffa", FACTION_JAFFA, 5, "close", "Gate Reinforcement"),
    "jaffa_staff_team_1": Card("jaffa_staff_team_1", "Staff Weapon Team", FACTION_JAFFA, 4, "agile", "Tactical Formation"),
    "jaffa_staff_team_2": Card("jaffa_staff_team_2", "Staff Weapon Team", FACTION_JAFFA, 4, "agile", "Tactical Formation"),
    "jaffa_staff_team_3": Card("jaffa_staff_team_3", "Staff Weapon Team", FACTION_JAFFA, 4, "agile", "Tactical Formation"),
    "jaffa_rebel_tech_1": Card("jaffa_rebel_tech_1", "Rebel Technician", FACTION_JAFFA, 3, "close", "Gate Reinforcement"),
    "jaffa_rebel_tech_2": Card("jaffa_rebel_tech_2", "Rebel Technician", FACTION_JAFFA, 3, "close", "Gate Reinforcement"),
    "jaffa_rebel_tech_3": Card("jaffa_rebel_tech_3", "Rebel Technician", FACTION_JAFFA, 3, "close", "Gate Reinforcement"),
    "jaffa_healer_1": Card("jaffa_healer_1", "Kelno'reem", FACTION_JAFFA, 5, "ranged", "Medical Evac"),
    "jaffa_healer_2": Card("jaffa_healer_2", "Kelno'reem", FACTION_JAFFA, 5, "ranged", "Medical Evac"),
    "jaffa_tegaris_ship": Card("jaffa_tegaris_ship", "Tel'tak Ship", FACTION_JAFFA, 4, "siege", None),
    "jaffa_resistance_recruit": Card("jaffa_resistance_recruit", "Resistance Recruit", FACTION_JAFFA, 7, "ranged", None),
    "jaffa_cadet_1": Card("jaffa_cadet_1", "Jaffa Training", FACTION_JAFFA, 2, "ranged", "Gate Reinforcement"),
    "jaffa_cadet_2": Card("jaffa_cadet_2", "Jaffa Training", FACTION_JAFFA, 2, "ranged", "Gate Reinforcement"),
    "jaffa_cadet_3": Card("jaffa_cadet_3", "Jaffa Training", FACTION_JAFFA, 2, "ranged", "Gate Reinforcement"),
    "jaffa_former_lord_jaffa": Card("jaffa_former_lord_jaffa", "Former System Lord Jaffa", FACTION_JAFFA, 5, "agile", None),
    "jaffa_zat_op": Card("jaffa_zat_op", "Zat'nik'tel Operative", FACTION_JAFFA, 4, "close", None),
    "jaffa_chakhal": Card("jaffa_chakhal", "Kah'l", FACTION_JAFFA, 5, "ranged", None),
    "jaffa_ktau_ally": Card("jaffa_ktau_ally", "Sodan Ally", FACTION_JAFFA, 8, "agile", None),
    "jaffa_shalchek_leader": Card("jaffa_shalchek_leader", "Shak'l", FACTION_JAFFA, 6, "close", "Inspiring Leadership"),
    "jaffa_trinium_cannon": Card("jaffa_trinium_cannon", "Siege Cannon", FACTION_JAFFA, 8, "siege", None),

    # --- Lucian Alliance ---
    "lucian_varro": Card("lucian_varro", "Varro", FACTION_LUCIAN, 10, "close", "Legendary Commander"),
    "lucian_netan": Card("lucian_netan", "Netan", FACTION_LUCIAN, 10, "close", "Legendary Commander"),
    "lucian_sodan_master": Card("lucian_sodan_master", "The Sodan Master", FACTION_LUCIAN, 10, "agile", "Legendary Commander"),
    "lucian_baal_clone": Card("lucian_baal_clone", "Ba'al Clone", FACTION_LUCIAN, 10, "siege", "Legendary Commander"),
    "lucian_foot_soldier_1": Card("lucian_foot_soldier_1", "Alliance Foot Soldier", FACTION_LUCIAN, 2, "close", "Tactical Formation"),
    "lucian_foot_soldier_2": Card("lucian_foot_soldier_2", "Alliance Foot Soldier", FACTION_LUCIAN, 2, "close", "Tactical Formation"),
    "lucian_foot_soldier_3": Card("lucian_foot_soldier_3", "Alliance Foot Soldier", FACTION_LUCIAN, 2, "close", "Tactical Formation"),
    "lucian_enforcer_1": Card("lucian_enforcer_1", "Alliance Enforcer", FACTION_LUCIAN, 3, "close", "Tactical Formation"),
    "lucian_enforcer_2": Card("lucian_enforcer_2", "Alliance Enforcer", FACTION_LUCIAN, 3, "close", "Tactical Formation"),
    "lucian_enforcer_3": Card("lucian_enforcer_3", "Alliance Enforcer", FACTION_LUCIAN, 3, "close", "Tactical Formation"),
    "lucian_smuggler_1": Card("lucian_smuggler_1", "Alliance Smuggler", FACTION_LUCIAN, 5, "close", "Tactical Formation"),
    "lucian_smuggler_2": Card("lucian_smuggler_2", "Alliance Smuggler", FACTION_LUCIAN, 5, "close", "Tactical Formation"),
    "lucian_prisoner": Card("lucian_prisoner", "Alliance Prisoner", FACTION_LUCIAN, 2, "close", None),
    "lucian_bounty": Card("lucian_bounty", "Bounty Hunter", FACTION_LUCIAN, 6, "close", None),
    "lucian_thug": Card("lucian_thug", "Alliance Thug", FACTION_LUCIAN, 3, "close", None),
    "lucian_mercenary": Card("lucian_mercenary", "Alliance Mercenary", FACTION_LUCIAN, 8, "ranged", None),
    "lucian_simeon": Card("lucian_simeon", "Simeon", FACTION_LUCIAN, 4, "close", "Deep Cover Agent"),
    "lucian_kiva": Card("lucian_kiva", "Kiva", FACTION_LUCIAN, 2, "close", "Deep Cover Agent"),
    "lucian_odyssey_spy": Card("lucian_odyssey_spy", "Odyssey Crew Deep Cover Agent", FACTION_LUCIAN, 1, "close", "Deep Cover Agent"),
    "lucian_grunt": Card("lucian_grunt", "Alliance Grunt", FACTION_LUCIAN, 3, "ranged", None),
    "lucian_sniper": Card("lucian_sniper", "Alliance Sniper", FACTION_LUCIAN, 3, "ranged", None),
    "lucian_dealer": Card("lucian_dealer", "Alliance Weapon Dealer", FACTION_LUCIAN, 4, "ranged", None),
    "lucian_heavy_gunner": Card("lucian_heavy_gunner", "Alliance Heavy Gunner", FACTION_LUCIAN, 5, "ranged", None),
    "lucian_ship_watch": Card("lucian_ship_watch", "Alliance Ship Watch", FACTION_LUCIAN, 4, "ranged", None),
    "lucian_commander": Card("lucian_commander", "Alliance Commander", FACTION_LUCIAN, 6, "ranged", None),
    "lucian_security": Card("lucian_security", "Alliance Security", FACTION_LUCIAN, 2, "ranged", None),
    "lucian_sodan_warrior": Card("lucian_sodan_warrior", "Sodan Warrior", FACTION_LUCIAN, 8, "agile", None),
    "lucian_medic_1": Card("lucian_medic_1", "Alliance Medical Evac", FACTION_LUCIAN, 3, "ranged", "Medical Evac"),
    "lucian_medic_2": Card("lucian_medic_2", "Alliance Medical Evac", FACTION_LUCIAN, 3, "ranged", "Medical Evac"),
    "lucian_ship_mechanic": Card("lucian_ship_mechanic", "Alliance Ship Mechanic", FACTION_LUCIAN, 2, "siege", "Medical Evac"),
    "lucian_cargo_ship_1": Card("lucian_cargo_ship_1", "Alliance Cargo Ship", FACTION_LUCIAN, 3, "siege", None),
    "lucian_cargo_ship_2": Card("lucian_cargo_ship_2", "Alliance Cargo Ship", FACTION_LUCIAN, 3, "siege", None),
    "lucian_hatak": Card("lucian_hatak", "Alliance Ha'tak", FACTION_LUCIAN, 6, "siege", None),
    "lucian_interceptor_1": Card("lucian_interceptor_1", "Alliance Interceptor", FACTION_LUCIAN, 5, "siege", None),
    "lucian_interceptor_2": Card("lucian_interceptor_2", "Alliance Interceptor", FACTION_LUCIAN, 5, "siege", None),
    "lucian_mothership": Card("lucian_mothership", "Alliance Mothership", FACTION_LUCIAN, 10, "siege", None),

    # --- Asgard ---
    "asgard_freyr": Card("asgard_freyr", "Freyr", FACTION_ASGARD, 10, "close", "Legendary Commander"),
    "asgard_loki": Card("asgard_loki", "Loki", FACTION_ASGARD, 10, "ranged", "Legendary Commander, Deploy Clones"),
    "asgard_heimdall": Card("asgard_heimdall", "Heimdall", FACTION_ASGARD, 8, "ranged", "Legendary Commander, Genetic Enhancement"),
    "asgard_thor": Card("asgard_thor", "Thor", FACTION_ASGARD, 12, "siege", "Legendary Commander, Inspiring Leadership"),
    "asgard_clone_incubator": Card("asgard_clone_incubator", "Clone Incubator", FACTION_ASGARD, 0, "close", "Activate Combat Protocol"),
    "asgard_medic": Card("asgard_medic", "Asgard Healing Pod", FACTION_ASGARD, 2, "close", "Medical Evac"),
    "asgard_clone_trooper_1": Card("asgard_clone_trooper_1", "Asgard Clone Trooper", FACTION_ASGARD, 3, "close", "Tactical Formation, Deploy Clones"),
    "asgard_clone_trooper_2": Card("asgard_clone_trooper_2", "Asgard Clone Trooper", FACTION_ASGARD, 3, "close", "Tactical Formation, Deploy Clones"),
    "asgard_clone_trooper_3": Card("asgard_clone_trooper_3", "Asgard Clone Trooper", FACTION_ASGARD, 3, "close", "Tactical Formation, Deploy Clones"),
    "asgard_scientist_1": Card("asgard_scientist_1", "Asgard Scientist", FACTION_ASGARD, 4, "ranged", None),
    "asgard_scientist_2": Card("asgard_scientist_2", "Asgard Scientist", FACTION_ASGARD, 4, "ranged", None),
    "asgard_technician_1": Card("asgard_technician_1", "Asgard Technician", FACTION_ASGARD, 4, "close", None),
    "asgard_technician_2": Card("asgard_technician_2", "Asgard Technician", FACTION_ASGARD, 4, "close", None),
    "asgard_elite_1": Card("asgard_elite_1", "Asgard Elite", FACTION_ASGARD, 6, "close", "Tactical Formation"),
    "asgard_elite_2": Card("asgard_elite_2", "Asgard Elite", FACTION_ASGARD, 6, "close", "Tactical Formation"),
    "asgard_diplomat": Card("asgard_diplomat", "Asgard Diplomat", FACTION_ASGARD, 6, "close", None),
    "asgard_observer": Card("asgard_observer", "Asgard Observer", FACTION_ASGARD, 6, "close", None),
    "asgard_berserker_1": Card("asgard_berserker_1", "Bilskirnir-class ship", FACTION_ASGARD, 5, "siege", "Tactical Formation"),
    "asgard_berserker_2": Card("asgard_berserker_2", "Bilskirnir-class ship", FACTION_ASGARD, 5, "siege", "Tactical Formation"),
    "asgard_imperfect_clone_1": Card("asgard_imperfect_clone_1", "Imperfect Clone", FACTION_ASGARD, 2, "ranged", "Tactical Formation"),
    "asgard_imperfect_clone_2": Card("asgard_imperfect_clone_2", "Imperfect Clone", FACTION_ASGARD, 2, "ranged", "Tactical Formation"),
    "asgard_beam_1": Card("asgard_beam_1", "Asgard Beam Tech", FACTION_ASGARD, 4, "ranged", "Gate Reinforcement"),
    "asgard_beam_2": Card("asgard_beam_2", "Asgard Beam Tech", FACTION_ASGARD, 4, "ranged", "Gate Reinforcement"),
    "asgard_beam_3": Card("asgard_beam_3", "Asgard Beam Tech", FACTION_ASGARD, 4, "ranged", "Gate Reinforcement"),
    "asgard_energy_drone_1": Card("asgard_energy_drone_1", "Energy Drone", FACTION_ASGARD, 3, "ranged", None),
    "asgard_energy_drone_2": Card("asgard_energy_drone_2", "Energy Drone", FACTION_ASGARD, 3, "ranged", None),
    "asgard_pulse_turret_1": Card("asgard_pulse_turret_1", "Energy Pulse Turret", FACTION_ASGARD, 6, "ranged", "Naquadah Overload"),
    "asgard_pulse_turret_2": Card("asgard_pulse_turret_2", "Energy Pulse Turret", FACTION_ASGARD, 6, "ranged", "Naquadah Overload"),
    "asgard_oneill_ship": Card("asgard_oneill_ship", "O'Neill-Class Mothership", FACTION_ASGARD, 8, "siege", "Command Network"),
    "asgard_defense_platform": Card("asgard_defense_platform", "Asgard Defense Platform", FACTION_ASGARD, 7, "siege", None),
    "asgard_daedalus_1": Card("asgard_daedalus_1", "Daedalus-Class Ship (Asgard Upgrades)", FACTION_ASGARD, 8, "siege", "Tactical Formation"),
    "asgard_daedalus_2": Card("asgard_daedalus_2", "Daedalus-Class Ship (Asgard Upgrades)", FACTION_ASGARD, 8, "siege", "Tactical Formation"),

    # --- Alteran (Ori & Ancients) ---
    # Heroes
    "alteran_adria": Card("alteran_adria", "Adria, The Orici", FACTION_ALTERAN, 12, "close", "Legendary Commander"),
    "alteran_doci": Card("alteran_doci", "The Doci", FACTION_ALTERAN, 10, "ranged", "Legendary Commander"),
    "alteran_merlin": Card("alteran_merlin", "Merlin (Moros)", FACTION_ALTERAN, 10, "siege", "Legendary Commander, Inspiring Leadership"),
    "alteran_morgan": Card("alteran_morgan", "Morgan Le Fay", FACTION_ALTERAN, 8, "ranged", "Legendary Commander, Medical Evac"),
    "alteran_oma": Card("alteran_oma", "Oma Desala", FACTION_ALTERAN, 10, "close", "Legendary Commander"),
    # Close Combat
    "alteran_prior_1": Card("alteran_prior_1", "Prior of the Ori", FACTION_ALTERAN, 5, "close", "Gate Reinforcement, Prior's Plague"),
    "alteran_prior_2": Card("alteran_prior_2", "Prior of the Ori", FACTION_ALTERAN, 5, "close", "Gate Reinforcement, Prior's Plague"),
    "alteran_prior_3": Card("alteran_prior_3", "Prior of the Ori", FACTION_ALTERAN, 5, "close", "Gate Reinforcement, Prior's Plague"),
    "alteran_follower_1": Card("alteran_follower_1", "Origin Follower", FACTION_ALTERAN, 2, "close", "Tactical Formation"),
    "alteran_follower_2": Card("alteran_follower_2", "Origin Follower", FACTION_ALTERAN, 2, "close", "Tactical Formation"),
    "alteran_follower_3": Card("alteran_follower_3", "Origin Follower", FACTION_ALTERAN, 2, "close", "Tactical Formation"),
    "alteran_warrior_1": Card("alteran_warrior_1", "Ori Warrior", FACTION_ALTERAN, 4, "close", "Gate Reinforcement"),
    "alteran_warrior_2": Card("alteran_warrior_2", "Ori Warrior", FACTION_ALTERAN, 4, "close", "Gate Reinforcement"),
    "alteran_tomin": Card("alteran_tomin", "Tomin", FACTION_ALTERAN, 6, "close", "Inspiring Leadership"),
    "alteran_knight": Card("alteran_knight", "Ancient Knight", FACTION_ALTERAN, 7, "close", "Ascension"),
    # Ranged
    "alteran_staff_1": Card("alteran_staff_1", "Prior (Staff of Power)", FACTION_ALTERAN, 4, "ranged", "Prior's Plague"),
    "alteran_staff_2": Card("alteran_staff_2", "Prior (Staff of Power)", FACTION_ALTERAN, 4, "ranged", "Prior's Plague"),
    "alteran_orlin": Card("alteran_orlin", "Orlin", FACTION_ALTERAN, 5, "ranged", "Deep Cover Agent"),
    "alteran_janus": Card("alteran_janus", "Janus", FACTION_ALTERAN, 6, "ranged", "Ascension"),
    "alteran_scientist_1": Card("alteran_scientist_1", "Ancient Scientist", FACTION_ALTERAN, 3, "ranged", "Tactical Formation"),
    "alteran_scientist_2": Card("alteran_scientist_2", "Ancient Scientist", FACTION_ALTERAN, 3, "ranged", "Tactical Formation"),
    "alteran_chaya": Card("alteran_chaya", "Chaya Sar", FACTION_ALTERAN, 5, "ranged", "Ascension"),
    "alteran_melia": Card("alteran_melia", "Melia", FACTION_ALTERAN, 4, "ranged", "Medical Evac"),
    "alteran_hallowed": Card("alteran_hallowed", "Hallowed Disciple", FACTION_ALTERAN, 1, "ranged", "Deep Cover Agent"),
    "alteran_drone_squad": Card("alteran_drone_squad", "Ancient Drone Squad", FACTION_ALTERAN, 6, "ranged", "Naquadah Overload"),
    # Siege
    "alteran_warship_1": Card("alteran_warship_1", "Ori Warship", FACTION_ALTERAN, 8, "siege", "Tactical Formation"),
    "alteran_warship_2": Card("alteran_warship_2", "Ori Warship", FACTION_ALTERAN, 8, "siege", "Tactical Formation"),
    "alteran_warship_3": Card("alteran_warship_3", "Ori Warship", FACTION_ALTERAN, 8, "siege", "Tactical Formation"),
    "alteran_supergate": Card("alteran_supergate", "Ori Supergate", FACTION_ALTERAN, 6, "siege", "Command Network"),
    "alteran_satellite": Card("alteran_satellite", "Ori Satellite Weapon", FACTION_ALTERAN, 5, "siege", "Prior's Plague"),
    "alteran_ark": Card("alteran_ark", "Ark of Truth", FACTION_ALTERAN, 0, "siege", "Command Network"),
    "alteran_sangraal": Card("alteran_sangraal", "Sangraal Device", FACTION_ALTERAN, 4, "siege", "Naquadah Overload"),
    "alteran_celestis": Card("alteran_celestis", "City of Celestis", FACTION_ALTERAN, 7, "siege", "Prior's Plague"),
    "alteran_ring_1": Card("alteran_ring_1", "Ori Ring Platform", FACTION_ALTERAN, 1, "siege", "Inspiring Leadership"),
    "alteran_ring_2": Card("alteran_ring_2", "Ori Ring Platform", FACTION_ALTERAN, 1, "siege", "Inspiring Leadership"),
    # Agile
    "alteran_plague": Card("alteran_plague", "Prior (Plague Bearer)", FACTION_ALTERAN, 3, "agile", "Life Force Drain"),
    "alteran_ascended_1": Card("alteran_ascended_1", "Ascended Ancient", FACTION_ALTERAN, 5, "agile", "Ascension"),
    "alteran_ascended_2": Card("alteran_ascended_2", "Ascended Ancient", FACTION_ALTERAN, 5, "agile", "Ascension"),
    "alteran_book": Card("alteran_book", "Book of Origin", FACTION_ALTERAN, 2, "agile", "Inspiring Leadership"),
    "alteran_flame_keeper": Card("alteran_flame_keeper", "Flame Keeper", FACTION_ALTERAN, 4, "agile", "Survival Instinct"),

    # --- Neutral Cards ---
    "neutral_ascended_daniel": Card("neutral_ascended_daniel", "Ascended Daniel Jackson", FACTION_NEUTRAL, 15, "close", "Legendary Commander"),
    "neutral_oma_desala": Card("neutral_oma_desala", "Oma Desala", FACTION_NEUTRAL, 15, "close", "Legendary Commander"),
    "neutral_mckay": Card("neutral_mckay", "Dr. Rodney McKay", FACTION_NEUTRAL, 7, "ranged", "Legendary Commander, Medical Evac"),
    "neutral_teyla": Card("neutral_teyla", "Teyla Emmagan", FACTION_NEUTRAL, 7, "close", "Legendary Commander"),
    "neutral_ancient_drone": Card("neutral_ancient_drone", "Ancients Drone", FACTION_NEUTRAL, 0, "ranged", "Deep Cover Agent, Legendary Commander"),
    "neutral_weir": Card("neutral_weir", "Dr. Elizabeth Weir", FACTION_NEUTRAL, 6, "close", "Legendary Commander"),
    "neutral_commanders_horn_1": Card("neutral_commanders_horn_1", "Tactical Network Uplink", FACTION_NEUTRAL, 0, "special", "Command Network"),
    "neutral_commanders_horn_2": Card("neutral_commanders_horn_2", "Tactical Network Uplink", FACTION_NEUTRAL, 0, "special", "Command Network"),
    "neutral_commanders_horn_3": Card("neutral_commanders_horn_3", "Tactical Network Uplink", FACTION_NEUTRAL, 0, "special", "Command Network"),
    "neutral_decoy_1": Card("neutral_decoy_1", "Asgard Ring Transport", FACTION_NEUTRAL, 0, "special", "Ring Transport"),
    "neutral_decoy_2": Card("neutral_decoy_2", "Asgard Ring Transport", FACTION_NEUTRAL, 0, "special", "Ring Transport"),
    "neutral_decoy_3": Card("neutral_decoy_3", "Asgard Ring Transport", FACTION_NEUTRAL, 0, "special", "Ring Transport"),
    "neutral_scorch_1": Card("neutral_scorch_1", "Naquadah Bomb", FACTION_NEUTRAL, 0, "special", "Naquadah Overload"),
    "neutral_scorch_2": Card("neutral_scorch_2", "Naquadah Bomb", FACTION_NEUTRAL, 0, "special", "Naquadah Overload"),
    "neutral_scorch_3": Card("neutral_scorch_3", "Naquadah Bomb", FACTION_NEUTRAL, 0, "special", "Naquadah Overload"),
    "neutral_biting_frost_1": Card("neutral_biting_frost_1", "Ice Planet Contingency", FACTION_NEUTRAL, 0, "weather", "Ice Planet Hazard"),
    "neutral_biting_frost_2": Card("neutral_biting_frost_2", "Ice Planet Contingency", FACTION_NEUTRAL, 0, "weather", "Ice Planet Hazard"),
    "neutral_biting_frost_3": Card("neutral_biting_frost_3", "Ice Planet Contingency", FACTION_NEUTRAL, 0, "weather", "Ice Planet Hazard"),
    "neutral_impenetrable_fog_1": Card("neutral_impenetrable_fog_1", "Nebula Field", FACTION_NEUTRAL, 0, "weather", "Nebula Interference"),
    "neutral_impenetrable_fog_2": Card("neutral_impenetrable_fog_2", "Nebula Field", FACTION_NEUTRAL, 0, "weather", "Nebula Interference"),
    "neutral_impenetrable_fog_3": Card("neutral_impenetrable_fog_3", "Nebula Field", FACTION_NEUTRAL, 0, "weather", "Nebula Interference"),
    "neutral_torrential_rain_1": Card("neutral_torrential_rain_1", "Micrometeorite Shower", FACTION_NEUTRAL, 0, "weather", "Asteroid Storm"),
    "neutral_torrential_rain_2": Card("neutral_torrential_rain_2", "Micrometeorite Shower", FACTION_NEUTRAL, 0, "weather", "Asteroid Storm"),
    "neutral_torrential_rain_3": Card("neutral_torrential_rain_3", "Micrometeorite Shower", FACTION_NEUTRAL, 0, "weather", "Asteroid Storm"),
    "neutral_clear_weather_1": Card("neutral_clear_weather_1", "Solar Flare/Ion Storm", FACTION_NEUTRAL, 0, "weather", "Wormhole Stabilization"),
    "neutral_clear_weather_2": Card("neutral_clear_weather_2", "Solar Flare/Ion Storm", FACTION_NEUTRAL, 0, "weather", "Wormhole Stabilization"),
    "neutral_clear_weather_3": Card("neutral_clear_weather_3", "Solar Flare/Ion Storm", FACTION_NEUTRAL, 0, "weather", "Wormhole Stabilization"),
    "neutral_skellige_storm_1": Card("neutral_skellige_storm_1", "Asgard Anti-Goa'uld Pulse", FACTION_NEUTRAL, 0, "weather", "Electromagnetic Pulse"),
    "neutral_skellige_storm_2": Card("neutral_skellige_storm_2", "Asgard Anti-Goa'uld Pulse", FACTION_NEUTRAL, 0, "weather", "Electromagnetic Pulse"),
    "neutral_skellige_storm_3": Card("neutral_skellige_storm_3", "Asgard Anti-Goa'uld Pulse", FACTION_NEUTRAL, 0, "weather", "Electromagnetic Pulse"),
    "decoy": Card("decoy", "Decoy", FACTION_NEUTRAL, 0, "close", None),

    # --- Unlockable Cards (from unlocks.py) ---
    "asgard_mothership": Card("asgard_mothership", "Asgard Mothership", FACTION_ASGARD, 10, "siege", "Draw 2 cards when played"),
    "ancient_drone": Card("ancient_drone", "Ancient Drone Chair", FACTION_NEUTRAL, 8, "ranged", "Naquadah Overload: Destroy lowest enemy unit"),
    "replicator_swarm_1": Card("replicator_swarm_1", "Replicator Swarm", FACTION_NEUTRAL, 4, "close", "Tactical Formation"),
    "replicator_swarm_2": Card("replicator_swarm_2", "Replicator Swarm", FACTION_NEUTRAL, 4, "close", "Tactical Formation"),
    "replicator_swarm_3": Card("replicator_swarm_3", "Replicator Swarm", FACTION_NEUTRAL, 4, "close", "Tactical Formation"),
    "wraith_hive_1": Card("wraith_hive_1", "Wraith Hive Ship", FACTION_NEUTRAL, 9, "siege", "Gate Reinforcement"),
    "wraith_hive_2": Card("wraith_hive_2", "Wraith Hive Ship", FACTION_NEUTRAL, 9, "siege", "Gate Reinforcement"),
    "wraith_hive_3": Card("wraith_hive_3", "Wraith Hive Ship", FACTION_NEUTRAL, 9, "siege", "Gate Reinforcement"),
    "ori_warship": Card("ori_warship", "Ori Warship", FACTION_NEUTRAL, 11, "siege", "Legendary Commander"),
    "atlantis_city": Card("atlantis_city", "City of Atlantis", FACTION_NEUTRAL, 10, "siege", "Legendary Commander, Inspiring Leadership"),
    "super_soldier": Card("super_soldier", "Anubis Super Soldier", FACTION_GOAULD, 7, "close", "Survival Instinct"),
    "prometheus_x303": Card("prometheus_x303", "Prometheus X-303", FACTION_TAURI, 8, "siege", "Draw 1 card when played"),
    "kull_warrior": Card("kull_warrior", "Kull Warrior Elite", FACTION_GOAULD, 8, "close", "Legendary Commander, Survival Instinct"),
    "puddle_jumper": Card("puddle_jumper", "Puddle Jumper", FACTION_NEUTRAL, 5, "agile", "Ring Transport: Return to hand to replay"),
    "sodan_warrior": Card("sodan_warrior", "Sodan Cloaked Warrior", FACTION_LUCIAN, 6, "close", "When played: Look at opponent's hand for 30s"),
    "tok_ra_operative": Card("tok_ra_operative", "Tok'ra Deep Cover Operative", FACTION_TAURI, 4, "ranged", "Deep Cover Agent"),
    "asgard_hammer": Card("asgard_hammer", "Thor's Hammer Device", FACTION_ASGARD, 0, "special", "Remove all Goa'uld units from both boards"),
    "zpm_power": Card("zpm_power", "Zero Point Module", FACTION_NEUTRAL, 0, "special", "Double all your siege units this round"),
    "merlin_device": Card("merlin_device", "Merlin's Anti-Ori Weapon", FACTION_NEUTRAL, 0, "special", "Naquadah Overload"),
    "dakara_superweapon": Card("dakara_superweapon", "Dakara Superweapon", FACTION_JAFFA, 12, "siege", "Legendary Commander"),
    "replicator_carter": Card("replicator_carter", "Replicator Carter", FACTION_NEUTRAL, 7, "close", "Survival Instinct"),
    "ancient_communication_stones": Card("ancient_communication_stones", "Ancient Communication Device", FACTION_NEUTRAL, 0, "special", "Reveal opponent's hand for 30 seconds"),
    "asuran_warship": Card("asuran_warship", "Asuran Aurora-class", FACTION_NEUTRAL, 10, "siege", "Grant ZPM, Tactical Formation"),
    "destiny_ship": Card("destiny_ship", "Ancient Ship Destiny", FACTION_NEUTRAL, 15, "siege", "Legendary Commander"),
    "neutral_quantum_mirror": Card("neutral_quantum_mirror", "Quantum Mirror", FACTION_NEUTRAL, 0, "special", "Shuffle your hand into deck, draw same number of cards. Ends hand reveal."),
}



# ============================================================================
# CARD BACK PLACEHOLDER (for opponent's hidden hand)
# ============================================================================

def create_card_back(width, height):
    """Create a procedurally generated card back image."""
    surface = pygame.Surface((width, height))
    
    # Base color - Dark blue/black
    surface.fill((20, 30, 50))
    
    # Stargate chevron pattern
    # Outer border
    pygame.draw.rect(surface, (100, 150, 200), (0, 0, width, height), 3, border_radius=8)
    
    # Inner decorative border
    pygame.draw.rect(surface, (60, 90, 130), (8, 8, width-16, height-16), 2, border_radius=6)
    
    # Center Stargate symbol
    center_x = width // 2
    center_y = height // 2
    
    # Outer ring
    pygame.draw.circle(surface, (100, 150, 200), (center_x, center_y), min(width, height) // 3, 3)
    
    # Inner ring
    pygame.draw.circle(surface, (60, 90, 130), (center_x, center_y), min(width, height) // 4, 2)
    
    # Chevron markers (9 small dots around the ring)
    import math
    chevron_radius = min(width, height) // 3 + 10
    for i in range(9):
        angle = (i / 9) * 2 * math.pi - math.pi / 2
        chevron_x = center_x + int(math.cos(angle) * chevron_radius)
        chevron_y = center_y + int(math.sin(angle) * chevron_radius)
        pygame.draw.circle(surface, (150, 180, 220), (chevron_x, chevron_y), 4)
    
    # Center symbol (triangle)
    triangle_size = min(width, height) // 8
    triangle_points = [
        (center_x, center_y - triangle_size),
        (center_x - triangle_size, center_y + triangle_size),
        (center_x + triangle_size, center_y + triangle_size)
    ]
    pygame.draw.polygon(surface, (150, 180, 220), triangle_points, 3)
    
    return surface

# Cache the card back so we don't recreate it every frame
_card_back_cache = {}

def get_card_back(width, height):
    """Get or create a card back of the specified size.
    
    Tries to load from assets/card_back.png first (high quality 4K version),
    falls back to procedurally generated version if PNG doesn't exist.
    """
    key = (width, height)
    if key not in _card_back_cache:
        # Try to load from PNG file first (high quality 4K version)
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        card_back_path = os.path.join(script_dir, "assets", "card_back.png")
        
        if os.path.exists(card_back_path):
            # Load and scale the high-quality PNG
            try:
                card_back_img = pygame.image.load(card_back_path)
                _card_back_cache[key] = pygame.transform.scale(card_back_img, (width, height))
            except Exception:
                # If loading fails, use procedural generation
                _card_back_cache[key] = create_card_back(width, height)
        else:
            # Fallback to generated version
            _card_back_cache[key] = create_card_back(width, height)
    
    return _card_back_cache[key]

# ============================================================================
# IMAGE CACHING OPTIMIZATION
# ============================================================================
_original_image_cache = {}
_last_loaded_size = None  # Cache to avoid redundant reloads

def _has_transparency(image_path):
    """Check if an image file likely has transparency based on format.

    PNG files with alpha channel need convert_alpha(), while opaque images
    can use the faster convert() method.
    """
    # Card images are PNG with alpha, so default to True for safety
    # Background/UI images ending in _bg typically don't need alpha
    lower_path = image_path.lower()
    if lower_path.endswith('_bg.png') or lower_path.endswith('_background.png'):
        return False
    # All card images use transparency for proper rendering
    return True


def reload_card_images():
    """
    Reload all card images with high-quality smoothscale and cache them.
    This ensures cards look sharp and render extremely fast.

    Optimization notes:
    - Uses SIMD-accelerated smoothscale (SSE2/NEON) via pygame-ce
    - Caches original images to avoid disk I/O on resize
    - Pre-renders hover images at 1.08x scale
    """
    global _last_loaded_size
    import os
    import game_config

    # Use HAND card dimensions (larger) - these look better and scale down well for board
    card_width = game_config.HAND_CARD_WIDTH if game_config.HAND_CARD_WIDTH > 0 else 115
    card_height = game_config.HAND_CARD_HEIGHT if game_config.HAND_CARD_HEIGHT > 0 else 173

    # OPTIMIZATION: Skip reload if size hasn't changed
    target_size = (card_width, card_height)
    if _last_loaded_size == target_size:
        print(f"  Using cached high-quality images at {card_width}x{card_height}")
        return

    _last_loaded_size = target_size
    print(f"Loading high-quality card images... Target size: {card_width}x{card_height}")

    for card_id, card in ALL_CARDS.items():
        card.rect = pygame.Rect(0, 0, card_width, card_height)

        # 1. Get the original image (from Cache or Disk)
        original_image = None
        if card.image_path in _original_image_cache:
            original_image = _original_image_cache[card.image_path]
        else:
            try:
                if os.path.exists(card.image_path):
                    # Load and convert with optimal format based on transparency needs
                    raw_image = pygame.image.load(card.image_path)
                    if _has_transparency(card.image_path):
                        original_image = raw_image.convert_alpha()
                    else:
                        original_image = raw_image.convert()  # Faster for opaque images
                    _original_image_cache[card.image_path] = original_image
            except (pygame.error, FileNotFoundError, OSError):
                pass

        # 2. Generate Scaled Versions using SMOOTHSCALE (SIMD-accelerated)
        if original_image:
            # High-quality scaling
            scaled = pygame.transform.smoothscale(original_image, (card_width, card_height))
            card.image = scaled.convert_alpha() if scaled.get_alpha() else scaled.convert()

            # Hover size (1.08x) - Pre-calculated for performance
            hover_w = int(card_width * 1.08)
            hover_h = int(card_height * 1.08)
            hover_scaled = pygame.transform.smoothscale(original_image, (hover_w, hover_h))
            card.hover_image = hover_scaled.convert_alpha() if hover_scaled.get_alpha() else hover_scaled.convert()
        else:
            # Fallback for missing images
            card.image = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
            card.image.fill((80, 80, 90))

            hover_w = int(card_width * 1.08)
            hover_h = int(card_height * 1.08)
            card.hover_image = pygame.Surface((hover_w, hover_h), pygame.SRCALPHA)
            card.hover_image.fill((100, 100, 110))

    print("High-quality card images loaded and optimized.")


def load_card_image(card):
    """Load image for a dynamically created card (tokens, clones, etc.)."""
    import os
    import game_config

    card_width = game_config.HAND_CARD_WIDTH if game_config.HAND_CARD_WIDTH > 0 else 115
    card_height = game_config.HAND_CARD_HEIGHT if game_config.HAND_CARD_HEIGHT > 0 else 173

    # Try to load from card's image_path
    if os.path.exists(card.image_path):
        try:
            original = pygame.image.load(card.image_path).convert_alpha()
            card.image = pygame.transform.smoothscale(original, (card_width, card_height)).convert_alpha()
            hover_w = int(card_width * 1.08)
            hover_h = int(card_height * 1.08)
            card.hover_image = pygame.transform.smoothscale(original, (hover_w, hover_h)).convert_alpha()
            return True
        except Exception as e:
            print(f"[card-image] Failed to load {card.image_path}: {e}")

    # Fallback: use faction-based placeholder
    card.image = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
    card.image.fill((60, 60, 80, 200))
    card.hover_image = pygame.Surface((int(card_width * 1.08), int(card_height * 1.08)), pygame.SRCALPHA)
    card.hover_image.fill((80, 80, 100, 200))
    return False


# ============================================================================
# USER CONTENT LOADING
# ============================================================================

def load_user_cards():
    """
    Load user-created cards from user_content folder.

    This function is called at game startup to inject user cards
    into the ALL_CARDS registry. User cards are created using
    ONLY existing game abilities.
    """
    try:
        from user_content_loader import load_user_content, get_user_cards

        # Load all user content (cards, leaders, factions)
        load_user_content()

        # Get user cards and add to ALL_CARDS
        user_cards = get_user_cards()
        for card_id, card in user_cards.items():
            if card_id not in ALL_CARDS:
                ALL_CARDS[card_id] = card
                print(f"[CARDS] Registered user card: {card_id}")

    except ImportError:
        # user_content_loader not available - skip
        pass
    except Exception as e:
        print(f"[CARDS] Error loading user cards: {e}")
