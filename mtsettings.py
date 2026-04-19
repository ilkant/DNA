'''
Ohjelman asetukset. Luetaan mtdna.ini-tiedostosta configparser-kirjastolla.
Jos ini-tiedostoa ei löydy, käytetään oletusarvoja.
'''

import configparser
import os

_INI_FILE = os.path.join(os.path.dirname(__file__), 'mtdna.ini')

_cfg = configparser.ConfigParser()
_cfg.read(_INI_FILE, encoding='utf-8')

def _get(section, key, fallback):
    return _cfg.get(section, key, fallback=fallback)

def _getbool(section, key, fallback):
    return _cfg.getboolean(section, key, fallback=fallback)

def _getint(section, key, fallback):
    return _cfg.getint(section, key, fallback=fallback)

# ── [general] ────────────────────────────────────────────
HAPLOGROUP = _get('general', 'haplogroup', 'U8a1a1b1')
FENCODING  = _get('general', 'fencoding',  'utf-8')
DATATYPE   = _get('general', 'datatype',   'json')
DEBUG      = _getbool('general', 'debug',      False)
SHOW_NAMES = _getbool('general', 'show_names', True)

# ── [paths] ───────────────────────────────────────────────
KITSFILE  = _get('paths', 'kitsfile',  'kits.csv')
DLDIR     = _get('paths', 'dldir',     '/home/ilpo/Lataukset/')
OUTPUTDIR = _get('paths', 'outputdir', '/data/sda1/PycharmProjects/DNA/Klusterointi/')

# ── [network] ─────────────────────────────────────────────
GDMAX = _getint('network', 'gdmax', 4)

# ── [colors] ──────────────────────────────────────────────
CLUSTER_NODE_COLOR        = _get('colors', 'cluster_node_color',        '#4a9fd4')
CLUSTER_NODE_BORDER_COLOR = _get('colors', 'cluster_node_border_color', '#2a6fa8')
MEMBER_NODE_COLOR         = _get('colors', 'member_node_color',         '#a8d4f0')
MEMBER_NODE_BORDER_COLOR  = _get('colors', 'member_node_border_color',  '#4a9fd4')
EDGE_COLOR                = _get('colors', 'edge_color',                '#2a6fa8')
MEMBER_EDGE_COLOR         = _get('colors', 'member_edge_color',         '#a8d4f0')
CLUSTER_LABEL_COLOR       = _get('colors', 'cluster_label_color',       '#ffffff')
MEMBER_LABEL_COLOR        = _get('colors', 'member_label_color',        '#333333')
BACKGROUND_COLOR          = _get('colors', 'background_color',          '#f5f5f5')

# ── [fonts] ───────────────────────────────────────────────
FONT_FAMILY        = _get('fonts', 'font_family',        'Arial')
CLUSTER_FONT_SIZE  = _getint('fonts', 'cluster_font_size',  9)
MEMBER_FONT_SIZE   = _getint('fonts', 'member_font_size',   7)
CLUSTER_FONT_BOLD  = _getbool('fonts', 'cluster_font_bold', False)
MEMBER_FONT_BOLD   = _getbool('fonts', 'member_font_bold',  False)
TITLE_FONT_SIZE    = _getint('fonts', 'title_font_size',    13)
TITLE_COLOR        = _get('fonts', 'title_color',           '#000000')


def save_to_ini():
    """Kirjoittaa nykyiset globaalit takaisin mtdna.ini-tiedostoon."""
    cfg = configparser.ConfigParser()

    cfg['general'] = {
        'haplogroup': HAPLOGROUP,
        'fencoding':  FENCODING,
        'datatype':   DATATYPE,
        'debug':      str(DEBUG).lower(),
        'show_names': str(SHOW_NAMES).lower(),
    }
    cfg['paths'] = {
        'kitsfile':  KITSFILE,
        'dldir':     DLDIR,
        'outputdir': OUTPUTDIR,
    }
    cfg['network'] = {
        'gdmax': str(GDMAX),
    }
    cfg['colors'] = {
        'cluster_node_color':        CLUSTER_NODE_COLOR,
        'cluster_node_border_color': CLUSTER_NODE_BORDER_COLOR,
        'member_node_color':         MEMBER_NODE_COLOR,
        'member_node_border_color':  MEMBER_NODE_BORDER_COLOR,
        'edge_color':                EDGE_COLOR,
        'member_edge_color':         MEMBER_EDGE_COLOR,
        'cluster_label_color':       CLUSTER_LABEL_COLOR,
        'member_label_color':        MEMBER_LABEL_COLOR,
        'background_color':          BACKGROUND_COLOR,
    }
    cfg['fonts'] = {
        'font_family':       FONT_FAMILY,
        'cluster_font_size': str(CLUSTER_FONT_SIZE),
        'member_font_size':  str(MEMBER_FONT_SIZE),
        'cluster_font_bold': str(CLUSTER_FONT_BOLD).lower(),
        'member_font_bold':  str(MEMBER_FONT_BOLD).lower(),
        'title_font_size':   str(TITLE_FONT_SIZE),
        'title_color':       TITLE_COLOR,
    }

    with open(_INI_FILE, 'w', encoding='utf-8') as f:
        cfg.write(f)
