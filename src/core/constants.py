"""
constants.py - Central config for Mutagen Arena.
Values pulled directly from the project spec sheet.

"""

# ── Screen ────────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1280, 720
FPS            = 60
TITLE          = "Mutagen Arena"

# ── Arena (larger than screen — camera scrolls) ───────────────────────────────
ARENA_W, ARENA_H = 2560, 1440

# ── Speed scale ───────────────────────────────────────────────────────────────
# All speed values in the spec are in "game units".
# Multiply by SPEED_SCALE to get pixels/second.
# e.g. player speed 5 → 5 * 64 = 320 px/s
SPEED_SCALE = 64

# ── Colors ────────────────────────────────────────────────────────────────────
C_BG           = (8,   10,  18)
C_FLOOR        = (15,  20,  35)
C_GRID         = (22,  32,  55)
C_WHITE        = (240, 240, 240)
C_GRAY         = (120, 120, 140)
C_DARK         = (30,  32,  44)

C_PLAYER       = (80,  220, 180)
C_PLAYER_BLADE = (200, 240, 255)

C_TANK         = (180,  55,  55)
C_STRIKER      = (220, 160,  35)
C_RANGED       = (70,  140, 220)
C_SUPPORT      = (160,  75, 220)
C_ALPHA_BOSS   = (255,  25,  75)

C_BULLET_PULSE = (255, 240,  80)
C_BULLET_ARC   = (80,  200, 255)
C_ENEMY_BULLET = (255,  75,  75)
C_TRAP         = (100, 255, 160)
C_SWING        = (200, 230, 255)

C_HP_BG        = (55,  18,  18)
C_HP_FG        = (200,  45,  45)
C_STAMINA_BG   = (18,  30,  55)
C_STAMINA_FG   = (60,  160, 255)
C_PURGE_BG     = (18,  40,  18)
C_PURGE_FG     = (45,  220,  90)

C_ACCENT       = (100, 220, 160)
C_WARN         = (255, 160,  35)
C_DANGER       = (255,  55,  55)
C_HUD_PANEL    = (8,   12,  24, 200)

# ── Player config  ────────────────────────────────────────────────────
PLAYER_HP              = 150
PLAYER_SPEED           = 5          # game units → * SPEED_SCALE px/s
PLAYER_RADIUS          = 27
PLAYER_HP_REGEN_WAVE   = 20         # HP restored at wave end
PLAYER_INV_FRAMES      = 0.5        # invincibility seconds after hit

PLAYER_MAX_STAMINA     = 100
PLAYER_STAMINA_REGEN   = 10         # per second
PLAYER_DASH_COST       = 25         # stamina per dash
PLAYER_DASH_SPEED_MULT = 2.0
PLAYER_DASH_DURATION   = 0.25       # seconds
PLAYER_MAX_LOADOUT     = 2          # weapons equipped at once

# ── Weapon configs ───────────────────────────────────────────────────
WEAPONS = {
    "Pulse Rifle": {
        "damage":            25,
        "range":             700,    # pixels
        "cooldown":          0.5,    # seconds
        "stamina_cost":      0,
        "projectile_speed":  15,     # game units → * SPEED_SCALE px/s
        "projectile_lifespan": 3,  # seconds (backup cap)
        "type":              "ranged",
        "proj_radius":       6,
        "color":             (255, 240, 80),
        "description":       "Fast burst. No stamina cost.",
    },
    "Shock Blade": {
        "damage":            50,
        "range":             100,     # pixels, melee hitbox radius
        "cooldown":          1.0,
        "stamina_cost":      10,
        "type":              "melee",
        "swing_duration":    0.18,   # how long the hitbox stays active
        "color":             (200, 230, 255),
        "description":       "Heavy melee. Hits everything in range.",
    },
    "Arc Launcher": {
        "damage":            80,
        "range":             500,    # pixels
        "cooldown":          2.0,
        "stamina_cost":      20,
        "projectile_speed":  10,     # game units → * SPEED_SCALE px/s
        "projectile_lifespan": 4,
        "type":              "ranged",
        "proj_radius":       12,
        "color":             (80, 200, 255),
        "description":       "Slow, massive damage. High stamina drain.",
    },
    "Stasis Trap": {
        "damage":            100,
        "range":             300,    # max placement distance from player
        "cooldown":          3.0,
        "stamina_cost":      15,
        "type":              "utility",
        "trap_radius":       75,     # trigger radius on ground
        "color":             (100, 255, 160),
        "description":       "Place a trap. Stasis + damage on trigger.",
    },
}

WEAPON_NAMES = list(WEAPONS.keys())   # consistent ordering

# ── Enemy configs ────────────────────────────────────────
ARCHETYPES = {
    "Tank": {
        "hp": 300, "speed": 2, "damage": 10,
        "attack_cd": 1.0, "resistance": 0.4,
        "radius": 40, "attack_range": 60,
        "color": C_TANK,
    },
    "Striker": {
        "hp": 80,  "speed": 6, "damage": 15,
        "attack_cd": 1.5, "resistance": 0.1,
        "radius": 20, "attack_range": 40,
        "color": C_STRIKER,
    },
    "Ranged": {
        "hp": 100, "speed": 3, "damage": 20,
        "attack_cd": 0.8, "resistance": 0.1,
        "radius": 25, "attack_range": 350,
        "projectile_speed": 8,
        "color": C_RANGED,
    },
    "Support": {
        "hp": 120, "speed": 3, "damage": 5,
        "attack_cd": 0.5, "resistance": 0.2,
        "radius": 25, "aoe_range": 200,
        "color": C_SUPPORT,
    },
}

MUTATION_DELTAS = {
    "hp": 20, "speed": 0.5, "damage": 5,
    "attack_cd": 0.2, "resistance": 0.05,
}

STAT_CAPS = {
    "hp": 1000, "speed": 12, "damage": 80,
    "attack_cd_min": 0.2, "resistance": 0.9,
}

# ── Wave settings  ──────────────────────────────────────────────────
STARTING_WAVE       = 1
ENEMIES_PER_WAVE    = 30
BOSS_WAVE_INTERVAL  = 10
PURGE_DURATION      = 300     # 5 minutes in seconds
MIN_SPAWN_DISTANCE  = 400     # pixels from player

# ── GA settings  ────────────────────────────────────────────────────
GA_TOURNAMENT_SIZE    = 3
GA_CROSSOVER_RATE     = 0.8
GA_POPULATION_SIZE    = 30
GA_BASE_MUTATION_RATE = 0.05
GA_MAX_MUTATION_RATE  = 0.30
GA_W1                 = 0.6   # weight: survival time
GA_W2                 = 0.4   # weight: damage dealt
GA_BASE_SIGMA                    = 0.15
LEDGER_STABLE_THRESHOLD_PCT      = 5.0
LEDGER_MAX_ENTRIES_PER_ARCHETYPE = 3

# ── SA settings  ────────────────────────────────────────────────────
SA_MAX_TEMPERATURE = 1.0
SA_COOLING_RATE    = 0.95

# ── Upgrades  ───────────────────────────────────────
UPGRADES = [
    {"name": "Adrenaline",   "desc": "+25% movement speed",     "stat": "speed",       "value": 0.25},
    {"name": "Iron Shell",   "desc": "+40 max HP",              "stat": "max_hp",      "value": 40},
    {"name": "Capacitor",    "desc": "+25 max stamina",         "stat": "max_stamina", "value": 25},
    {"name": "Overcharge",   "desc": "+30% weapon damage",      "stat": "damage",      "value": 0.30},
    {"name": "Coolant",      "desc": "-25% weapon cooldowns",   "stat": "cooldown",    "value": -0.25},
    {"name": "Phase Dash",   "desc": "+1 dash charge (stamina reset)", "stat": "dash", "value": 1},
    {"name": "Stamina Coil", "desc": "+50% stamina regen",      "stat": "stam_regen",  "value": 0.50},
    {"name": "Hollow Tip",   "desc": "+20% projectile speed",   "stat": "proj_speed",  "value": 0.20},
]