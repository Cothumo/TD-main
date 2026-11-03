# Ambient Ink - shared settings for build_ink.py (TouchDesigner) and tools/preview.py (offline preview).
# Uniform sources: 'f:<col>' = column of the features table at the current frame, 'p:<Par>' = custom parameter on the
# component, or one of the specials (frame, dt, reset, aspect, resh); anything else is a numeric literal.
TITLE = 'Ambient Ink Live (third layer of TDA.16, driven by Ableton track "2")'
NAME = 'ink_track2'               # component built in /project1
PREFIX = 'ink_track2'             # render file names
FPS = 30
W, H = 720, 1280                  # 9:16 for Stories / Shorts (Non-Commercial TD caps at 1280; Commercial: 1080, 1920)
                                  # set 1280, 720 for landscape - the analysis adapts the currents (H > W = portrait)
SIM_W, SIM_H = 1024, 1024         # particle state texture = max particle count (1,048,576)
TEST_AUDIO = 'Avernus.mp3'        # looping test file (Source = file), next to this file
LIVE = True                       # features come from the Script CHOP 'live' (live_features.py)
ANALYZER = 'live_features.py'
SHADERS = {'sim': 'ink_sim.glsl', 'vertex': 'ink_vertex.glsl', 'pixel': 'ink_pixel.glsl',
           'accum': 'ink_accum.glsl', 'post': 'ink_post.glsl'}
BLUR_PARAM = 'Diffusionsize'      # Blur TOP size (px) on the accumulated ink -> soft halo
EXPO_UNIFORM = ('post', 'uF', 1)  # what the preview scales when it draws fewer particles than the build

# name, default, min, max (slider range), help
PARAMS = [
    ('Quality',       0.45,  0.05, 1.0, 'fraction of the 1M particles drawn (render always uses 1.0)'),
    ('Particlesize',  1.3,  0.5,  4.0, 'sprite radius in px at 720 high'),
    ('Ink',           0.7,  0.0,  3.0, 'amount of ink each particle carries'),
    ('Opacity',       3.0,  0.0,  6.0, 'how quickly ink turns opaque black'),
    ('Diffusion',     1.0,  0.0,  2.0, 'soft halo of dissolved ink around the dense parts'),
    ('Diffusionsize', 20.0, 2.0,  40.0, 'halo radius in px'),
    ('Dilution',      1.5,  0.0,  3.0, 'how fast old ink pales'),
    ('Spreadgrowth',  2.0,  0.0,  3.0, 'how much old ink spreads out'),
    ('Turbulence',    1.6,  0.0,  3.0, 'billowing curl-noise flow (grows as the ink ages)'),
    ('Tendrils',      1.5,  0.0,  3.0, 'fine wisps (driven by the high band)'),
    ('Condense',      0.25,  0.0,  3.0, 'how fast ink condenses out of the water along the drifting seams (louder = more)'),
    ('Jet',           0.0, 0.0,  1.0, 'share of the ink that still enters as a thin jet from the upstream edge (0 = none)'),
    ('Lowpush',       1.0,  0.0,  3.0, 'bass: pressure wave on low hits + slow gyre of the whole water'),
    ('Flutter',       1.0,  0.0,  3.0, 'treble: fine fast trembling of the tendrils + whirl flicks on hi-hats'),
    ('Sprayamount',   0.7,  0.0,  3.0, 'treble: ink in the hi-hat droplet sprays'),
    ('Sprayspeed',    1.0,  0.0,  3.0, 'treble: how far the droplets shoot'),
    ('Shimmer',       1.0,  0.0,  3.0, 'treble: fine flicker of droplets and specks'),
    ('Billow',        0.4,  0.0,  3.0, 'vortex-ring roll-up of each puff (mushroom caps)'),
    ('Puffsize',      2.5,  0.3,  2.5, 'size of the puffs'),
    ('Jetspeed',      1.4,  0.0,  3.0, 'injection speed of the jet and the puffs'),
    ('Current',       1.2,  0.0,  3.0, 'drift of the water (direction follows the song sections)'),
    ('Buoyancy',      0.3,  -1.0, 1.0, 'ink rises (+) or sinks (-)'),
    ('Flowspeed',     1.0,  0.0,  3.0, 'global simulation speed'),
    ('Lifetime',      0.6,  0.3,  1.3, 'how long ink stays visible'),
    ('Reactivity',    1.0,  0.0,  2.5, 'how strongly the music modulates the flow'),
    ('Dust',          0.0,  0.0,  2.0, 'dark specks floating in the water'),
    ('Trails',        0.25, 0.0,  0.95, 'frame feedback (smooth streaks)'),
    ('Dof',           0.6,  0.0,  3.0, 'depth-of-field blur on near/far ink'),
    ('Light',         0.0,  0.0,  1.5, 'side light across the paper'),
    ('Lightangle',    0.0,  -180.0, 180.0, 'direction the light comes from (degrees, 0 = right)'),
    ('Paperdetail',   0.0,  0.0,  2.0, 'paper texture and marks'),
    ('Grain',         0.0,  0.0,  2.0, 'film grain'),
    ('Vignette',      0.0,  0.0,  1.5, 'edge darkening'),
    ('Invert',        0.0,  0.0,  1.0, '1 = white ink on black'),
    ('Vibration',     1.5,  0.0,  3.0, 'the ink shakes and trembles on unstable sounds (vib column of the features)'),
    ('Solarpull',     2.0,  0.0,  3.0, 'while the sphere is there: its gravity pulls the plasma back -> arcs and loops'),
    ('Swirl',         1.0,  0.0,  3.0, 'while the sphere is there: the plasma swirls round it'),
    ('Wrap',          1.0,  0.0,  2.0, 'the sphere is solid: the ink flows round it'),
    ('Formpull',      0.0,  0.0,  3.0, '(not used here)'),
    ('Disruption',    0.4,  0.0,  3.0, 'percussion hits tear the ink into sliding strips with a stutter echo (dis column of the features)'),
]
COLORS = [                        # RGB parameters: name, default
    ('Paper',  (1.0, 1.0, 1.0)),           # white: the layer multiplies over neith_live (white = no change)
    ('Inkcolor', (0.015, 0.015, 0.015)),
    ('Dilutecolor', (0.32, 0.32, 0.32)),
    ('Accent', (0.015, 0.015, 0.015)),    # hi-hat spray ink (same black; set a colour for a second ink)
]

PUFF = lambda s: ('uP%d' % s, ['f:p%d_x' % s, 'f:p%d_y' % s, 'f:p%d_ang' % s, 'f:p%d_str' % s])
SPRAY = lambda s: ('uS%d' % s, ['f:s%d_x' % s, 'f:s%d_y' % s, 'f:s%d_ang' % s, 'f:s%d_str' % s])
UNIFORMS = {
    'sim': [
        ('uT', ['f:phase', 'f:spin', 'dt', 'reset']),
        ('uA', ['f:level', 'f:low', 'f:mid', 'f:high']),
        ('uB', ['f:onset', 'f:bright', 'f:arc', 'f:build']),
        ('uC', ['f:cur_x', 'f:cur_y', 'aspect', '0']),
        ('uAg', ['f:p0_age', 'f:p1_age', 'f:p2_age', 'f:p3_age']),
        ('uAh', ['f:p4_age', 'f:p5_age', '0', '0']),
    ] + [PUFF(s) for s in range(6)] + [
        ('uK', ['p:Turbulence', 'p:Current', 'p:Jetspeed', 'p:Billow']),
        ('uL', ['p:Reactivity', 'p:Lifetime', 'p:Tendrils', 'p:Buoyancy']),
        ('uM', ['p:Puffsize', 'p:Flowspeed', 'p:Lowpush', 'p:Sprayspeed']),
        ('uN', ['f:kick', 'f:kick_id', 'f:hat', '0']),
        ('uO', ['p:Flutter', 'f:hat_id', 'p:Jet', 'p:Condense']),
        ('uSa', ['f:s0_age', 'f:s1_age', 'f:s2_age', 'f:s3_age']),
    ] + [SPRAY(s) for s in range(4)] + [
        ('uG1', ['g:wOx', 'g:wOy', 'g:wRo', 'g:behind']),     # the sphere (sphere/geometry): plasma born on its limb
        ('uG2', ['g:wMx', 'g:wMy', 'g:wRm', 'p:Wrap']),
        ('uG3', ['g:limb', 'p:Solarpull', 'p:Swirl', 'g:rad']),
        ('uG4', ['g:fa', 'g:fb', 'g:fm', 'g:fs']),
        ('uG5', ['g:flood', 'p:Formpull', 'g:hard', '0']),
    ],
    'mat': [
        ('uA', ['f:level', 'f:low', 'f:mid', 'f:high']),
        ('uB', ['f:onset', 'f:bright', 'f:arc', 'f:build']),
        ('uR', ['p:Particlesize', 'resh', 'p:Dof', 'p:Ink']),
        ('uS', ['p:Reactivity', 'p:Dilution', 'p:Spreadgrowth', 'p:Dust']),
        ('uU', ['p:Quality', 'aspect', 'p:Lifetime', 'p:Jet']),
        ('uV', ['p:Sprayamount', 'p:Shimmer', 'f:phase', 'f:hat']),
    ],
    'accum': [
        ('uK', ['p:Trails', 'reset', '0', '0']),
    ],
    'post': [
        ('uF', ['frame', 'p:Opacity', 'p:Diffusion', 'p:Grain']),
        ('uG', ['f:arc', 'f:level', 'p:Reactivity', 'p:Invert']),
        ('uH', ['p:Paperr', 'p:Paperg', 'p:Paperb', 'p:Vignette']),
        ('uI', ['p:Inkcolorr', 'p:Inkcolorg', 'p:Inkcolorb', 'p:Paperdetail']),
        ('uJ', ['p:Dilutecolorr', 'p:Dilutecolorg', 'p:Dilutecolorb', 'p:Light']),
        ('uK', ['aspect', 'p:Lightangle', 'f:vib', 'p:Vibration']),
        ('uL', ['p:Accentr', 'p:Accentg', 'p:Accentb', '0']),
        ('uM', ['f:dis', 'f:dis_id', 'p:Disruption', '0']),
    ],
}

# extra parameters of the layer (Look page): how it sits over the picture below it
LAYER_PARAMS = [
    ('Layeramount', 0.5, 0.0, 1.0, 'how strongly the ink is laid over neith_live (0 = off)'),
    ('Inktone', 0.08, 0.0, 1.0, 'grey of dense, fresh ink over neith_live (0 = black, 1 = white); it never inverts'),
    ('Inktonelight', 0.6, 0.0, 1.0, 'grey of thin, old ink: the ink spans the greys between this and Inktone'),
    ('Inkmatch', 0.5, 0.0, 1.0, 'how much the ink takes on a darker shade of the picture beneath it (0 = its own greys, 1 = only the picture, darkened)'),
    ('Inkthreshold', 0.3, 0.0, 0.8, 'faint ink below this is left out, so only the real ink shows over neith_live'),
]
