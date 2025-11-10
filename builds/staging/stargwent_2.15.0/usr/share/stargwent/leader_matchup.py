"""
Leader Matchup Animation System
Creates unique confrontations based on Stargate SG-1 lore for every leader combination.
"""
import pygame
import math
import random


# Leader matchup quotes and context based on Stargate SG-1 lore
LEADER_MATCHUPS = {
    # O'Neill matchups
    ("Col. Jack O'Neill", "Apophis"): {
        "quote": "In the middle of my backswing?!",
        "context": "O'Neill's casual defiance against Apophis's threats",
        "color": (255, 100, 100)
    },
    ("Col. Jack O'Neill", "Lord Yu"): {
        "quote": "For crying out loud...",
        "context": "O'Neill's exasperation with System Lord politics",
        "color": (200, 150, 50)
    },
    ("Col. Jack O'Neill", "Ba'al"): {
        "quote": "We've been down this road before.",
        "context": "Their repeated confrontations across time",
        "color": (150, 50, 150)
    },
    ("Col. Jack O'Neill", "Anubis"): {
        "quote": "You're the reason we can't have nice things.",
        "context": "The Ancient threat returns",
        "color": (100, 100, 100)
    },
    ("Col. Jack O'Neill", "Teal'c"): {
        "quote": "Indeed.",
        "context": "Brothers in arms, mutual respect",
        "color": (100, 200, 255)
    },
    
    # Teal'c matchups
    ("Teal'c", "Apophis"): {
        "quote": "I have pledged my life to destroy you.",
        "context": "Former First Prime turns against his god",
        "color": (200, 50, 50)
    },
    ("Teal'c", "Bra'tac"): {
        "quote": "Master Bra'tac, old friend.",
        "context": "Master and apprentice, warriors united",
        "color": (200, 150, 100)
    },
    ("Teal'c", "Gerak"): {
        "quote": "You have chosen the path of the false gods.",
        "context": "Ideological conflict within the Jaffa",
        "color": (180, 100, 50)
    },
    
    # Daniel Jackson matchups
    ("Dr. Daniel Jackson", "Apophis"): {
        "quote": "Your reign of terror ends today.",
        "context": "Daniel's wife Sha're was taken by Apophis",
        "color": (200, 80, 80)
    },
    ("Dr. Daniel Jackson", "Oma Desala"): {
        "quote": "The path to enlightenment is never easy.",
        "context": "Teacher and student, ascension journey",
        "color": (255, 255, 200)
    },
    ("Dr. Daniel Jackson", "Anubis"): {
        "quote": "You're playing with forces you don't understand.",
        "context": "Ancient knowledge vs power hunger",
        "color": (100, 100, 150)
    },
    
    # Carter matchups
    ("Dr. Samantha Carter", "Ba'al"): {
        "quote": "Your arrogance will be your downfall.",
        "context": "Scientific mind vs godly ego",
        "color": (150, 100, 200)
    },
    ("Dr. Samantha Carter", "Fifth"): {
        "quote": "Emotions don't make you human.",
        "context": "The Replicator who loved her",
        "color": (150, 150, 200)
    },
    
    # Hammond matchups
    ("Gen. George Hammond", "Apophis"): {
        "quote": "Earth will not bow to false gods.",
        "context": "Commander defending his world",
        "color": (200, 100, 50)
    },
    
    # System Lord vs System Lord
    ("Apophis", "Lord Yu"): {
        "quote": "The oldest alliance is no alliance.",
        "context": "System Lords never truly trust each other",
        "color": (200, 180, 50)
    },
    ("Apophis", "Ba'al"): {
        "quote": "Only one shall rule supreme.",
        "context": "Power struggle among the Goa'uld",
        "color": (180, 100, 180)
    },
    ("Ba'al", "Lord Yu"): {
        "quote": "Age does not grant wisdom.",
        "context": "The upstart vs the ancient",
        "color": (200, 150, 100)
    },
    
    # Asgard matchups
    ("Thor", "Anubis"): {
        "quote": "The Asgard will not allow your ascension.",
        "context": "Advanced race vs corrupted Ancient",
        "color": (150, 200, 255)
    },
    ("Thor", "Col. Jack O'Neill"): {
        "quote": "Greetings, O'Neill of Minnesota.",
        "context": "Alliance of two great warriors",
        "color": (100, 150, 255)
    },
    ("Thor Supreme Commander", "Anubis"): {
        "quote": "Your Ancient knowledge is no match for Asgard technology.",
        "context": "Supreme Commander faces the half-ascended threat",
        "color": (150, 200, 255)
    },
    ("Hermiod", "Col. Jack O'Neill"): {
        "quote": "Your impulsiveness will be our downfall.",
        "context": "Asgard engineer's frustration with humans",
        "color": (120, 180, 255)
    },
    
    # Unlockable Tau'ri leaders
    ("Gen. Landry", "Ba'al"): {
        "quote": "This is MY command. You will not pass.",
        "context": "Landry's no-nonsense leadership",
        "color": (100, 150, 200)
    },
    ("Dr. McKay", "Anubis"): {
        "quote": "I've run the calculations. You lose.",
        "context": "McKay's scientific arrogance",
        "color": (150, 180, 255)
    },
    ("Jonas Quinn", "Anubis"): {
        "quote": "I've seen how this ends. It's not good for you.",
        "context": "Jonas's premonition ability",
        "color": (180, 200, 255)
    },
    ("Catherine Langford", "Apophis"): {
        "quote": "I've been studying your kind for 50 years.",
        "context": "The archaeologist who started it all",
        "color": (200, 180, 150)
    },
    
    # Unlockable Goa'uld leaders
    ("Ba'al", "Anubis"): {
        "quote": "Even death cannot stop my return.",
        "context": "The clone master vs the ascended",
        "color": (150, 100, 200)
    },
    ("Hathor (Unlockable)", "Col. Jack O'Neill"): {
        "quote": "You will serve me, Jack O'Neill.",
        "context": "The seductress Goa'uld",
        "color": (200, 100, 150)
    },
    ("Cronus", "Teal'c"): {
        "quote": "You dare challenge a System Lord?",
        "context": "Ancient Goa'uld meets rebellion",
        "color": (180, 100, 50)
    },
    
    # Unlockable Jaffa leaders
    ("Master Bra'tac", "Apophis"): {
        "quote": "This day of reckoning is long overdue, false god!",
        "context": "The master tactician's final stand",
        "color": (200, 150, 80)
    },
    ("Ka'lel", "Gerak"): {
        "quote": "We must unite, not divide!",
        "context": "Warrior training vs political division",
        "color": (180, 140, 70)
    },
    ("Ishta", "Apophis"): {
        "quote": "The Hak'tyl will never serve you again.",
        "context": "Female warriors break free",
        "color": (200, 160, 100)
    },
    
    # Unlockable Lucian Alliance leaders
    ("Netan", "Col. Jack O'Neill"): {
        "quote": "The black market always wins, Colonel.",
        "context": "Smuggler vs military",
        "color": (150, 100, 150)
    },
    ("Vala Mal Doran", "Dr. Daniel Jackson"): {
        "quote": "Oh, come on Daniel! Where's your sense of adventure?",
        "context": "The treasure hunter who stole Daniel's heart",
        "color": (200, 150, 200)
    },
    ("Anateo", "Teal'c"): {
        "quote": "Even Jaffa can be bought.",
        "context": "Mercenary pragmatism",
        "color": (150, 120, 150)
    },
    ("Kiva", "Gen. Hammond"): {
        "quote": "Surprise is the greatest weapon.",
        "context": "Lucian tactics",
        "color": (160, 100, 160)
    },
    
    # More Asgard unlockables
    ("Penegal", "Ba'al"): {
        "quote": "Your clones are primitive compared to Asgard technology.",
        "context": "Cloning masters clash",
        "color": (120, 200, 255)
    },
    ("Aegir", "Anubis"): {
        "quote": "The High Council has decreed your defeat.",
        "context": "Asgard authority",
        "color": (140, 210, 255)
    },
    
    # Jaffa matchups
    ("Bra'tac", "Apophis"): {
        "quote": "The day of reckoning has come, false god.",
        "context": "Old warrior's rebellion",
        "color": (200, 100, 50)
    },
    
    # Default fallback for any unspecified matchup
    "default": {
        "quote": "The battle for the galaxy begins.",
        "context": "Two great powers collide",
        "color": (150, 150, 200)
    }
}


def get_matchup_data(leader1_name, leader2_name):
    """Get matchup data for two leaders, checking both orderings."""
    # Try both orderings
    matchup = LEADER_MATCHUPS.get((leader1_name, leader2_name))
    if matchup:
        return matchup
    
    # Try reverse
    matchup = LEADER_MATCHUPS.get((leader2_name, leader1_name))
    if matchup:
        return matchup
    
    # Generate dynamic matchup based on factions if no specific one exists
    return generate_dynamic_matchup(leader1_name, leader2_name)


def generate_dynamic_matchup(leader1_name, leader2_name):
    """Generate a matchup based on faction relationships."""
    # Simple faction-based relationships
    tau_ri_leaders = ["O'Neill", "Hammond", "Carter", "Jackson", "Mitchell", "Landry", 
                      "McKay", "Jonas Quinn", "Catherine"]
    goauld_leaders = ["Apophis", "Yu", "Ba'al", "Sokar", "Anubis", "Hathor", "Cronus"]
    jaffa_leaders = ["Teal'c", "Bra'tac", "Gerak", "Ishta", "Ka'lel", "Master Bra'tac", "Rak'nor"]
    asgard_leaders = ["Thor", "Freyr", "Loki", "Heimdall", "Hermiod", "Penegal", "Aegir", 
                     "Supreme Commander"]
    lucian_leaders = ["Vulkar", "Sodan", "Netan", "Vala", "Anateo", "Kiva"]
    
    def get_faction(name):
        for leader in tau_ri_leaders:
            if leader in name:
                return "Tau'ri"
        for leader in goauld_leaders:
            if leader in name:
                return "Goa'uld"
        for leader in jaffa_leaders:
            if leader in name:
                return "Jaffa"
        for leader in asgard_leaders:
            if leader in name:
                return "Asgard"
        return "Unknown"
    
    faction1 = get_faction(leader1_name)
    faction2 = get_faction(leader2_name)
    
    # Tau'ri vs Goa'uld
    if (faction1 == "Tau'ri" and faction2 == "Goa'uld") or (faction1 == "Goa'uld" and faction2 == "Tau'ri"):
        return {
            "quote": "The Tau'ri will never kneel to false gods!",
            "context": "Earth's defenders vs System Lords",
            "color": (200, 100, 100)
        }
    
    # Jaffa vs Goa'uld
    elif (faction1 == "Jaffa" and faction2 == "Goa'uld") or (faction1 == "Goa'uld" and faction2 == "Jaffa"):
        return {
            "quote": "The Jaffa are free! Your reign ends now!",
            "context": "The rebellion against slavery",
            "color": (200, 150, 50)
        }
    
    # Asgard vs Goa'uld
    elif (faction1 == "Asgard" and faction2 == "Goa'uld") or (faction1 == "Goa'uld" and faction2 == "Asgard"):
        return {
            "quote": "Asgard technology surpasses your stolen tricks.",
            "context": "Advanced civilization vs parasites",
            "color": (150, 200, 255)
        }
    
    # Same faction (civil war/rivalry)
    elif faction1 == faction2:
        return {
            "quote": f"Only one {faction1} shall emerge victorious.",
            "context": "Internal conflict",
            "color": (180, 180, 100)
        }
    
    # Default
    return LEADER_MATCHUPS["default"]


class LeaderMatchupAnimation:
    """Cinematic leader matchup animation with collision and floating cards."""
    
    def __init__(self, leader1, leader2, screen_width, screen_height):
        self.leader1 = leader1
        self.leader2 = leader2
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
        self.elapsed = 0
        self.duration = 8000  # 8 seconds total - more time to read the quote!
        self.finished = False
        
        # Get matchup data
        self.matchup = get_matchup_data(leader1['name'], leader2['name'])
        
        # Load background PNG if available
        self.background_image = self.load_matchup_background(leader1['name'], leader2['name'])
        
        # Check if this is Tau'ri vs Goa'uld (Iris should be present)
        self.show_iris = self.is_tauri_vs_goauld()
        
        # Card positions
        self.card_width = 200
        self.card_height = 300
        
        # Leader 1 (player) - starts off screen left, ends bottom left
        self.l1_start_x = -self.card_width
        self.l1_start_y = screen_height // 2 - self.card_height // 2
        self.l1_collision_x = screen_width // 2 - self.card_width // 2 - 50
        self.l1_end_x = 50
        self.l1_end_y = screen_height - self.card_height - 50
        
        # Leader 2 (opponent) - starts off screen right, ends top left
        self.l2_start_x = screen_width + self.card_width
        self.l2_start_y = screen_height // 2 - self.card_height // 2
        self.l2_collision_x = screen_width // 2 + self.card_width // 2 + 50
        self.l2_end_x = 50
        self.l2_end_y = 50
        
        # Lightning bolts
        self.lightning_bolts = []
    
    def load_matchup_background(self, leader1_name, leader2_name):
        """Load background PNG for this leader matchup."""
        import os
        
        # Sanitize leader names for filenames
        def sanitize_name(name):
            # Remove common titles
            name = name.replace("Col. ", "").replace("Gen. ", "").replace("Dr. ", "")
            name = name.replace("Master ", "").replace("Supreme Commander ", "")
            # Remove special characters and make lowercase with underscores
            name = name.replace("'", "").replace(".", "").replace(" ", "_").lower()
            return name
        
        l1_clean = sanitize_name(leader1_name)
        l2_clean = sanitize_name(leader2_name)
        
        print(f"\n=== Leader Matchup Background Loading ===")
        print(f"Leader 1: {leader1_name} -> {l1_clean}")
        print(f"Leader 2: {leader2_name} -> {l2_clean}")
        
        # Try both orders (player vs AI and AI vs player)
        filenames = [
            f"leader_matchup_{l1_clean}_vs_{l2_clean}.png",
            f"leader_matchup_{l2_clean}_vs_{l1_clean}.png",
            f"matchup_{l1_clean}_{l2_clean}.png",
            f"matchup_{l2_clean}_{l1_clean}.png"
        ]
        
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        print(f"Assets directory: {assets_dir}")
        
        for filename in filenames:
            filepath = os.path.join(assets_dir, filename)
            print(f"Trying: {filename} ... ", end="")
            if os.path.exists(filepath):
                try:
                    image = pygame.image.load(filepath)
                    # Scale to screen size
                    image = pygame.transform.scale(image, (self.screen_width, self.screen_height))
                    print(f"✓ LOADED!")
                    return image
                except Exception as e:
                    print(f"✗ Error: {e}")
            else:
                print("Not found")
        
        # No background found
        print("⚠ No matchup background found, using animated fallback")
        return None
    
    def is_tauri_vs_goauld(self):
        """Check if this matchup is Tau'ri vs Goa'uld."""
        tauri_faction = self.leader1.get('faction') == "Tau'ri" or self.leader2.get('faction') == "Tau'ri"
        goauld_faction = self.leader1.get('faction') == "Goa'uld" or self.leader2.get('faction') == "Goa'uld"
        return tauri_faction and goauld_faction
    
    def update(self, dt):
        """Update animation state."""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
        return not self.finished
    
    def get_progress(self):
        """Get animation progress (0.0 to 1.0)."""
        return min(1.0, self.elapsed / self.duration)
    
    def ease_in_out(self, t):
        """Smooth easing function."""
        return t * t * (3.0 - 2.0 * t)
    
    def get_leader_positions(self, progress):
        """Calculate leader card positions based on progress."""
        # Phase 1 (0-0.25): Cards fly in from sides (2 seconds)
        # Phase 2 (0.25-0.375): Collision at center (1 second)
        # Phase 3 (0.375-1.0): Cards float to final positions and LINGER (5 seconds for reading)
        
        if progress < 0.25:
            # Flying in
            t = progress / 0.25
            t = self.ease_in_out(t)
            l1_x = self.l1_start_x + (self.l1_collision_x - self.l1_start_x) * t
            l1_y = self.l1_start_y
            l2_x = self.l2_start_x + (self.l2_collision_x - self.l2_start_x) * t
            l2_y = self.l2_start_y
        
        elif progress < 0.375:
            # Collision phase - shake and lightning
            shake = int(10 * math.sin(progress * 100))
            l1_x = self.l1_collision_x + shake
            l1_y = self.l1_start_y + shake
            l2_x = self.l2_collision_x - shake
            l2_y = self.l2_start_y - shake
        
        else:
            # Floating to final positions (and staying there for reading)
            t = (progress - 0.375) / 0.625
            t = self.ease_in_out(t)
            # Complete movement by 50% (at 4.5 seconds), then hold
            if t > 0.5:
                t = 1.0
            else:
                t = t * 2
            l1_x = self.l1_collision_x + (self.l1_end_x - self.l1_collision_x) * t
            l1_y = self.l1_start_y + (self.l1_end_y - self.l1_start_y) * t
            l2_x = self.l2_collision_x + (self.l2_end_x - self.l2_collision_x) * t
            l2_y = self.l2_start_y + (self.l2_end_y - self.l2_start_y) * t
        
        return (int(l1_x), int(l1_y), int(l2_x), int(l2_y))
    
    def draw(self, surface):
        """Draw the leader matchup animation."""
        progress = self.get_progress()
        
        # ALWAYS draw the animated Stargate horizon first (it's beautiful!)
        self.draw_stargate_horizon(surface, progress)
        
        # If PNG background exists, draw it WITH transparency so Stargate shows through
        if self.background_image:
            # Create semi-transparent version of the background
            temp_surface = self.background_image.copy()
            temp_surface.set_alpha(180)  # 0-255, lower = more transparent (180 = 70% visible)
            surface.blit(temp_surface, (0, 0))
            
            # Add slight darkening for text readability
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 50))  # Gentle darkening
            surface.blit(overlay, (0, 0))
        
        # Get card positions
        l1_x, l1_y, l2_x, l2_y = self.get_leader_positions(progress)
        
        # Draw energy field during collision (0.25-0.375)
        if 0.25 <= progress < 0.375:
            self.draw_collision_effect(surface, progress)
        
        # Draw leader cards
        self.draw_leader_card(surface, self.leader1, l1_x, l1_y, is_player=True)
        self.draw_leader_card(surface, self.leader2, l2_x, l2_y, is_player=False)
        
        # Draw VS text during collision
        if 0.2 <= progress < 0.45:
            vs_alpha = int(255 * min(1.0, (progress - 0.2) / 0.1))
            if progress > 0.35:
                vs_alpha = int(255 * (1.0 - (progress - 0.35) / 0.1))
            
            vs_font = pygame.font.SysFont("Arial", 120, bold=True)
            vs_text = vs_font.render("VS", True, (255, 255, 255))
            vs_text.set_alpha(vs_alpha)
            vs_rect = vs_text.get_rect(center=(self.center_x, self.center_y))
            surface.blit(vs_text, vs_rect)
        
        # Draw quote and context - APPEARS EARLIER AND STAYS VISIBLE
        if progress > 0.45:
            quote_alpha = int(255 * min(1.0, (progress - 0.45) / 0.15))
            
            quote_font = pygame.font.SysFont("Arial", 42, bold=True)
            quote_text = quote_font.render(f'"{self.matchup["quote"]}"', True, self.matchup["color"])
            quote_text.set_alpha(quote_alpha)
            quote_rect = quote_text.get_rect(center=(self.center_x, self.screen_height - 150))
            surface.blit(quote_text, quote_rect)
            
            context_font = pygame.font.SysFont("Arial", 28, italic=True)
            context_text = context_font.render(self.matchup["context"], True, (200, 200, 200))
            context_text.set_alpha(quote_alpha)
            context_rect = context_text.get_rect(center=(self.center_x, self.screen_height - 100))
            surface.blit(context_text, context_rect)
    
    def draw_stargate_horizon(self, surface, progress):
        """Draw animated Stargate event horizon background - BIGGER and more detailed."""
        # Dark space background
        surface.fill((5, 5, 15))
        
        # Much bigger Stargate!
        ring_radius = min(self.screen_width, self.screen_height) // 2 - 100  # Almost full screen
        ring_thickness = 60
        
        # Inner ring (Stargate actual gate)
        inner_ring_radius = ring_radius - ring_thickness
        
        # Outer decorative ring (stone carved circle)
        outer_decoration_radius = ring_radius + 30
        pygame.draw.circle(surface, (60, 55, 50), (self.center_x, self.center_y), outer_decoration_radius, 8)
        
        # Main Stargate ring (metallic with segments)
        # Draw multiple rings for depth
        for i in range(4):
            offset = i * 3
            shade = 70 + i * 10
            pygame.draw.circle(surface, (shade, shade, shade + 10), 
                             (self.center_x, self.center_y), 
                             ring_radius - offset, 3)
        
        # Main ring body (metallic gray)
        pygame.draw.circle(surface, (90, 90, 100), (self.center_x, self.center_y), ring_radius, ring_thickness)
        
        # Ring highlights (metallic shine)
        pygame.draw.circle(surface, (120, 120, 130), (self.center_x, self.center_y), ring_radius + 5, 3)
        pygame.draw.circle(surface, (70, 70, 80), (self.center_x, self.center_y), ring_radius - ring_thickness - 5, 3)
        
        # Metal segments on ring (like the actual Stargate)
        num_segments = 36
        for i in range(num_segments):
            angle = (i / num_segments) * 2 * math.pi
            segment_x = self.center_x + int(math.cos(angle) * (ring_radius - ring_thickness // 2))
            segment_y = self.center_y + int(math.sin(angle) * (ring_radius - ring_thickness // 2))
            
            # Alternating segment colors for detail
            if i % 2 == 0:
                pygame.draw.circle(surface, (80, 80, 90), (segment_x, segment_y), 6)
            else:
                pygame.draw.circle(surface, (100, 100, 110), (segment_x, segment_y), 4)
        
        # 9 CHEVRONS (bigger and more detailed)
        chevron_positions = []
        for i in range(9):
            angle = (i / 9) * 2 * math.pi - math.pi / 2  # Start at top
            chevron_x = self.center_x + int(math.cos(angle) * ring_radius)
            chevron_y = self.center_y + int(math.sin(angle) * ring_radius)
            chevron_positions.append((chevron_x, chevron_y))
            
            # Chevrons light up during collision phase
            if 0.25 <= progress < 0.375:
                locked = int((progress - 0.25) / 0.125 * 9)
                if i < locked:
                    color = (255, 200, 50)  # Gold/orange locked
                    glow_color = (255, 220, 100, 180)
                else:
                    color = (80, 80, 90)  # Dark unlocked
                    glow_color = None
            else:
                color = (80, 80, 90)
                glow_color = None
            
            # Chevron glow
            if glow_color:
                glow_surface = pygame.Surface((80, 80), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, glow_color, (40, 40), 35)
                surface.blit(glow_surface, (chevron_x - 40, chevron_y - 40))
            
            # Chevron shape (triangular/wedge shape)
            chevron_size = 30
            chevron_points = [
                (chevron_x, chevron_y - chevron_size),
                (chevron_x + chevron_size // 2, chevron_y + chevron_size // 2),
                (chevron_x - chevron_size // 2, chevron_y + chevron_size // 2)
            ]
            pygame.draw.polygon(surface, color, chevron_points)
            pygame.draw.polygon(surface, (120, 120, 130), chevron_points, 3)
        
        # Check if we should show the Iris (Tau'ri vs Goa'uld)
        if self.show_iris:
            self.draw_iris(surface, progress, inner_ring_radius)
        else:
            self.draw_event_horizon(surface, progress, inner_ring_radius)
    
    def draw_iris(self, surface, progress, radius):
        """Draw the Tau'ri Iris (closed metal shield) for Tau'ri vs Goa'uld matchups."""
        # Iris opens during collision, closes after
        if progress < 0.25:
            # Closed
            iris_open_amount = 0.0
        elif progress < 0.375:
            # Opening during collision
            iris_open_amount = (progress - 0.25) / 0.125
        else:
            # Stays open
            iris_open_amount = 1.0
        
        # Iris blades (20 segments forming a shield)
        num_blades = 20
        blade_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        blade_center = (radius, radius)
        
        for i in range(num_blades):
            angle_start = (i / num_blades) * 2 * math.pi
            angle_end = ((i + 1) / num_blades) * 2 * math.pi
            
            # Blade closes from outside to center
            blade_inner_radius = int(radius * iris_open_amount)
            blade_outer_radius = radius
            
            if blade_inner_radius < blade_outer_radius:
                # Draw blade segment
                points = []
                for a in [angle_start, angle_end]:
                    # Outer point
                    points.append((
                        blade_center[0] + int(math.cos(a) * blade_outer_radius),
                        blade_center[1] + int(math.sin(a) * blade_outer_radius)
                    ))
                for a in [angle_end, angle_start]:
                    # Inner point
                    points.append((
                        blade_center[0] + int(math.cos(a) * blade_inner_radius),
                        blade_center[1] + int(math.sin(a) * blade_inner_radius)
                    ))
                
                # Metallic blade color (titanium/steel)
                blade_color = (140, 140, 150) if i % 2 == 0 else (120, 120, 130)
                pygame.draw.polygon(blade_surface, blade_color, points)
                pygame.draw.polygon(blade_surface, (100, 100, 110), points, 2)
        
        # Draw center hub
        if iris_open_amount < 1.0:
            hub_radius = int(radius * 0.15)
            pygame.draw.circle(blade_surface, (100, 100, 110), blade_center, hub_radius)
            pygame.draw.circle(blade_surface, (80, 80, 90), blade_center, hub_radius, 3)
        
        # Blit iris to screen
        surface.blit(blade_surface, (self.center_x - radius, self.center_y - radius))
        
        # If iris is opening, show event horizon appearing behind it
        if iris_open_amount > 0:
            self.draw_event_horizon(surface, progress, int(radius * iris_open_amount))
    
    def draw_event_horizon(self, surface, progress, radius):
        """Draw the event horizon (watery, rippling effect)."""
        horizon_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        
        # Create multiple layers of ripples
        num_ripples = 15
        for i in range(num_ripples):
            ripple_progress = (progress * 3 + i / num_ripples) % 1.0
            ripple_radius = int(radius * ripple_progress)
            ripple_alpha = int(80 * (1.0 - ripple_progress))
            
            if ripple_alpha > 0:
                # Blue/cyan watery color
                ripple_color = (50, 150, 255, ripple_alpha)
                pygame.draw.circle(horizon_surface, ripple_color, 
                                 (radius, radius), 
                                 ripple_radius, 4)
        
        # Vertical water distortion effect (more pronounced)
        for y in range(0, radius * 2, 3):
            distortion = int(12 * math.sin(progress * 10 + y * 0.08))
            # This creates wave-like distortion
        
        # Base water layer (shimmering and pulsing)
        water_alpha = int(140 + 60 * math.sin(progress * 8))
        water_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(water_surface, (30, 120, 200, water_alpha),
                         (radius, radius), radius)
        
        # Composite the event horizon
        horizon_x = self.center_x - radius
        horizon_y = self.center_y - radius
        surface.blit(water_surface, (horizon_x, horizon_y))
        surface.blit(horizon_surface, (horizon_x, horizon_y))
        
        # Energy particles floating around (more particles for bigger gate)
        num_particles = 50
        for i in range(num_particles):
            particle_angle = (progress * 2 + i / num_particles) * 2 * math.pi
            particle_dist = radius - 80 + 40 * math.sin(progress * 5 + i)
            particle_x = self.center_x + int(math.cos(particle_angle) * particle_dist)
            particle_y = self.center_y + int(math.sin(particle_angle) * particle_dist)
            particle_size = int(4 + 3 * math.sin(progress * 10 + i * 2))
            particle_alpha = int(180 + 75 * math.sin(progress * 8 + i))
            
            particle_color = (100, 200, 255, min(255, max(0, particle_alpha)))
            particle_surface = pygame.Surface((particle_size * 2, particle_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surface, particle_color, (particle_size, particle_size), particle_size)
            surface.blit(particle_surface, (particle_x - particle_size, particle_y - particle_size))
    
    def draw_collision_effect(self, surface, progress):
        """Draw lightning and energy effects during collision."""
        # Energy burst at center
        collision_progress = (progress - 0.3) / 0.2
        burst_radius = int(300 * collision_progress)
        burst_alpha = int(200 * (1.0 - collision_progress))
        
        if burst_alpha > 0:
            burst_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            pygame.draw.circle(burst_surface, (*self.matchup["color"], burst_alpha), 
                             (self.center_x, self.center_y), burst_radius)
            surface.blit(burst_surface, (0, 0))
        
        # Lightning bolts
        for i in range(8):
            angle = (i / 8) * 2 * math.pi + progress * 10
            length = 200 + 100 * math.sin(progress * 20 + i)
            end_x = int(self.center_x + math.cos(angle) * length)
            end_y = int(self.center_y + math.sin(angle) * length)
            
            # Draw jagged lightning
            points = [(self.center_x, self.center_y)]
            segments = 5
            for s in range(1, segments + 1):
                t = s / segments
                x = int(self.center_x + (end_x - self.center_x) * t + random.randint(-20, 20))
                y = int(self.center_y + (end_y - self.center_y) * t + random.randint(-20, 20))
                points.append((x, y))
            
            if len(points) > 1:
                pygame.draw.lines(surface, self.matchup["color"], False, points, 3)
    
    def draw_leader_card(self, surface, leader, x, y, is_player):
        """Draw a leader card with portrait image if available."""
        import os
        
        card_rect = pygame.Rect(x, y, self.card_width, self.card_height)
        
        # Try to load leader portrait image
        leader_card_id = leader.get('card_id', '')
        leader_image = None
        
        if leader_card_id:
            assets_dir = os.path.join(os.path.dirname(__file__), "assets")
            portrait_path = os.path.join(assets_dir, f"{leader_card_id}_leader.png")
            
            if os.path.exists(portrait_path):
                try:
                    leader_image = pygame.image.load(portrait_path)
                    # Scale to card size
                    leader_image = pygame.transform.scale(leader_image, (self.card_width, self.card_height))
                except Exception as e:
                    print(f"Warning: Could not load leader portrait {portrait_path}: {e}")
        
        # If image loaded, use it as the card
        if leader_image:
            surface.blit(leader_image, (x, y))
            # Add golden border around the image
            pygame.draw.rect(surface, (255, 215, 0), card_rect, 5, border_radius=15)
        else:
            # Fallback: Draw colored rectangle with text (original behavior)
            faction_colors = {
                "Tau'ri": (100, 150, 255),
                "Goa'uld": (200, 50, 50),
                "Jaffa Rebellion": (200, 140, 50),
                "Lucian Alliance": (150, 50, 150),
                "Asgard": (50, 200, 150)
            }
            bg_color = faction_colors.get(leader.get('faction', 'Neutral'), (100, 100, 100))
            
            # Draw card
            pygame.draw.rect(surface, bg_color, card_rect, border_radius=15)
            pygame.draw.rect(surface, (255, 215, 0), card_rect, 5, border_radius=15)
            
            # Leader name
            name_font = pygame.font.SysFont("Arial", 24, bold=True)
            name_text = name_font.render(leader['name'], True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(x + self.card_width // 2, y + 30))
            surface.blit(name_text, name_rect)
            
            # Ability
            ability_font = pygame.font.SysFont("Arial", 16)
            ability_text = ability_font.render(leader.get('ability', ''), True, (220, 220, 220))
            # Wrap text if too long
            if ability_text.get_width() > self.card_width - 20:
                words = leader.get('ability', '').split()
                line1 = ""
                line2 = ""
                for word in words:
                    if len(line1) < len(leader.get('ability', '')) // 2:
                        line1 += word + " "
                    else:
                        line2 += word + " "
                ability_text1 = ability_font.render(line1.strip(), True, (220, 220, 220))
                ability_text2 = ability_font.render(line2.strip(), True, (220, 220, 220))
                surface.blit(ability_text1, (x + 10, y + self.card_height - 80))
                surface.blit(ability_text2, (x + 10, y + self.card_height - 60))
            else:
                surface.blit(ability_text, (x + 10, y + self.card_height - 60))
