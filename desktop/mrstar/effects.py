"""The 58 effect IDs selectable in the Mr Star ModeFragment UI.

Names were extracted from resources/res/values/strings.xml. ModeFragment creates
13 further "Flow" items (63–75), but does not display that tab. We deliberately
do not expose those unverified IDs as normal supported presets.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Effect:
    id: int
    name: str
    category: str

# Preserve the Android app's displayed category ordering and ID mapping.
EFFECT_IDS = {
    'Basic': (1, 2, 3, 4, 7, 10, 26, 27, 29, 30, 31, 32),
    'Opening & closing': tuple(range(35, 45)),
    'Transition': tuple(range(45, 55)),
    'Running water': tuple(range(55, 63)),
    'Tailing': tuple(range(76, 84)),
    'Running': tuple(range(84, 94)),
}

EFFECT_NAMES = {
    1:'Automatic loop', 2:'Symphony', 3:'Colorful energy', 4:'Colorful jumps',
    7:'7 colors strobe', 10:'7 colors gradient',
    26:'Colorful fluttering', 27:'Red-green-blue fluttering',
    29:'Colorful brushing', 30:'Red-green-blue color brushing',
    31:'Yellow-cyan-purple color brushing', 32:'Colorful brush color brush closed-pull',
    35:'7 colors opening-closing', 36:'Red-green-blue opening-closing',
    37:'Yellow-cyan-purple opening-closes', 38:'Red opening-closing',
    39:'Green opening-closing', 40:'Blue opening-closing',
    41:'Yellow opening-closing', 42:'Cyan opening-closing',
    43:'purple opening-closing', 44:'White opening-closing',
    45:'7 colors light-dark transition', 46:'Blue-red-green light-dark transition',
    47:'Violet-green-yellow light-dark transition',
    48:'6 colors light-dark transition red', 49:'6 colors light-dark transition green',
    50:'6 colors light-dark transition blue', 51:'6 colors light-dark transition cyan',
    52:'6 colors light-dark transition yellow', 53:'6 colors light-dark transition purple',
    54:'6 colors light-dark transition white',
    55:'7 colors flowing water', 56:'Blue-green-red running water',
    57:'Purple-green-yellow running water', 58:'Red-green running water',
    59:'Green-blue running water', 60:'Yellow-blue running water',
    61:'Yellow-cyan running water', 62:'Blue-purple running water',
    76:'7 colors trailing', 77:'Red trailing', 78:'Green trailing',
    79:'Blue trailing', 80:'Yellow trailing', 81:'Cyan tailing',
    82:'Purple tailing', 83:'White trailing',
    84:'Red running', 85:'Green running', 86:'Blue running',
    87:'Yellow running', 88:'Cyan running', 89:'Purple running',
    90:'White running', 91:'7 colors running',
    92:'Blue-green-red running', 93:'Purple-cyan-yellow running',
}

EFFECTS = tuple(Effect(i, EFFECT_NAMES[i], category)
                for category, ids in EFFECT_IDS.items() for i in ids)
assert len(EFFECTS) == 58 and len({effect.id for effect in EFFECTS}) == 58
