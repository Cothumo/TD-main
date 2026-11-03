// Ambient Ink - particle state update (GLSL TOP, rgba32float, fed back through sim_fb).
// One texel = one particle: xyz = position, w = generation + remaining life (fract: 1 -> 0, 0 = dead waiting
// for its puff); w < 0 = waiting -w seconds before the first emission.
// Ink WELLS UP in mid-water: six soft sources drift slowly through the frame, each swelling and fading on its own
// cycle, releasing more ink when the music is louder (wider with the bass); puffs bloom in mid-water on swells and
// low hits; an optional thin jet (Jet) still trickles in from the upstream edge.
// Nothing pulls the ink onto shapes: it is injected and carried by
// the water - a drifting current, vortex-ring roll-up of each puff (mushroom caps) and curl-noise billows that
// grow as the ink ages - so it stretches into real tendrils.
// Lows and highs MOVE differently. Bass = big, slow, heavy: the large billows swell, a slow gyre turns the whole
// water, every low hit thumps it with a pressure wave and drives the puffs. Treble = small, fast, nervous: a fine
// fast flow makes the tendrils flutter, every hi-hat flicks little whirls into them and fires a spray of droplets.
uniform vec4 uT;   // phase, spin, dt, reset
uniform vec4 uA;   // level, low, mid, high
uniform vec4 uB;   // onset, bright, arc, build
uniform vec4 uC;   // cur_x, cur_y, aspect, 0
uniform vec4 uAg;  // age of puff slots 0..3 (s, 999 = none)
uniform vec4 uAh;  // age of puff slots 4, 5
uniform vec4 uP0;  // puff slot 0: x (fraction of half-width), y, direction (rad), strength
uniform vec4 uP1;
uniform vec4 uP2;
uniform vec4 uP3;
uniform vec4 uP4;
uniform vec4 uP5;
uniform vec4 uK;   // Turbulence, Current, Jetspeed, Billow
uniform vec4 uL;   // Reactivity, Lifetime, Tendrils, Buoyancy
uniform vec4 uM;   // Puffsize, Flowspeed, Lowpush, Sprayspeed
uniform vec4 uN;   // kick, kick_id, hat, 0
uniform vec4 uO;   // Flutter, hat_id, Jet, Condense
uniform vec4 uSa;  // age of spray slots 0..3
uniform vec4 uS0;  // spray slot 0: x (fraction of half-width), y, direction (rad), strength
uniform vec4 uS1;
uniform vec4 uS2;
uniform vec4 uS3;

out vec4 fragColor;

const float TAU = 6.28318531;
// particle classes by h.w (ink_vertex.glsl uses the same split)
const float DUSTF = 0.96;         // above: dark specks floating in the water
const float SPRAYF = 0.78;        // above: fine droplets fired by hi-hats (second ink colour)
const float BASEF = 0.50;         // above: the continuous jet; below: the six puff slots

// ---------------------------------------------------------------- hashing
uvec4 pcg4d(uvec4 v)
{
	v = v * 1664525u + 1013904223u;
	v.x += v.y * v.w; v.y += v.z * v.x; v.z += v.x * v.y; v.w += v.y * v.z;
	v ^= v >> 16u;
	v.x += v.y * v.w; v.y += v.z * v.x; v.z += v.x * v.y; v.w += v.y * v.z;
	return v;
}
vec4 rnd4(uint id, uint salt) { return vec4(pcg4d(uvec4(id, salt, id ^ 0x9E3779B9u, salt * 7u + 1u))) * (1.0 / 4294967295.0); }

// ---------------------------------------------------------------- simplex noise with analytic gradient
// (Ashima Arts / Stefan Gustavson, MIT licence)
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 10.0) * x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v, out vec3 gradient)
{
	const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
	const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
	vec3 i = floor(v + dot(v, C.yyy));
	vec3 x0 = v - i + dot(i, C.xxx);
	vec3 g = step(x0.yzx, x0.xyz);
	vec3 l = 1.0 - g;
	vec3 i1 = min(g.xyz, l.zxy);
	vec3 i2 = max(g.xyz, l.zxy);
	vec3 x1 = x0 - i1 + C.xxx;
	vec3 x2 = x0 - i2 + C.yyy;
	vec3 x3 = x0 - D.yyy;
	i = mod289(i);
	vec4 p = permute(permute(permute(
		i.z + vec4(0.0, i1.z, i2.z, 1.0))
		+ i.y + vec4(0.0, i1.y, i2.y, 1.0))
		+ i.x + vec4(0.0, i1.x, i2.x, 1.0));
	float n_ = 0.142857142857;
	vec3 ns = n_ * D.wyz - D.xzx;
	vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
	vec4 x_ = floor(j * ns.z);
	vec4 y_ = floor(j - 7.0 * x_);
	vec4 x = x_ * ns.x + ns.yyyy;
	vec4 y = y_ * ns.x + ns.yyyy;
	vec4 h = 1.0 - abs(x) - abs(y);
	vec4 b0 = vec4(x.xy, y.xy);
	vec4 b1 = vec4(x.zw, y.zw);
	vec4 s0 = floor(b0) * 2.0 + 1.0;
	vec4 s1 = floor(b1) * 2.0 + 1.0;
	vec4 sh = -step(h, vec4(0.0));
	vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
	vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
	vec3 p0 = vec3(a0.xy, h.x);
	vec3 p1 = vec3(a0.zw, h.y);
	vec3 p2 = vec3(a1.xy, h.z);
	vec3 p3 = vec3(a1.zw, h.w);
	vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
	p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
	vec4 m = max(0.5 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
	vec4 m2 = m * m;
	vec4 m4 = m2 * m2;
	vec4 pdotx = vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3));
	vec4 temp = m2 * m * pdotx;
	gradient = -8.0 * (temp.x * x0 + temp.y * x1 + temp.z * x2 + temp.w * x3);
	gradient += m4.x * p0 + m4.y * p1 + m4.z * p2 + m4.w * p3;
	gradient *= 105.0;
	return 105.0 * dot(m4, pdotx);
}

vec3 curlNoise(vec3 q)
{
	vec3 g1, g2, g3;
	snoise(q, g1);
	snoise(q + vec3(31.416, -47.853, 12.793), g2);
	snoise(q + vec3(-233.145, -113.408, -185.31), g3);
	return vec3(g3.y - g2.z, g1.z - g3.x, g2.x - g1.y);
}

// ---------------------------------------------------------------- helpers
vec3 rotX(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(p.x, c * p.y - s * p.z, s * p.y + c * p.z); }
vec3 rotY(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(c * p.x + s * p.z, p.y, -s * p.x + c * p.z); }
vec3 rotZ(vec3 p, float a) { float c = cos(a), s = sin(a); return vec3(c * p.x - s * p.y, s * p.x + c * p.y, p.z); }
vec3 sph(vec2 r) { float z = 2.0 * r.x - 1.0, a = TAU * r.y, s = sqrt(max(0.0, 1.0 - z * z)); return vec3(s * cos(a), z, s * sin(a)); }

vec4 puff(int s) { return s == 0 ? uP0 : s == 1 ? uP1 : s == 2 ? uP2 : s == 3 ? uP3 : s == 4 ? uP4 : uP5; }
float puffAge(int s) { return s < 4 ? uAg[s] : uAh[s - 4]; }
vec4 spray(int s) { return s == 0 ? uS0 : s == 1 ? uS1 : s == 2 ? uS2 : uS3; }

// lifetimes in seconds (ink_vertex.glsl repeats these to know each particle's age)
float lifeBase(vec4 h2) { return mix(6.0, 13.0, h2.z) * uL.y; }
float lifeCondensed(vec4 h2) { return mix(5.0, 11.0, h2.z) * uL.y; }
float lifePuff(vec4 h2) { return mix(8.0, 16.0, h2.z) * uL.y; }
float lifeSpray(vec4 h2) { return mix(1.8, 4.0, h2.z) * uL.y; }

// ink wells: six soft sources drifting slowly through the water (smooth Lissajous paths), each one swelling and
// fading on its own slow cycle - ink wells up in mid-water in several places instead of streaming in from an edge
vec3 wellPos(uint site, float t)
{
	float s = float(site);
	return vec3(sin(t * (0.11 + 0.017 * s) + s * 1.7) * 0.62 * uC.z,
	            sin(t * (0.083 + 0.013 * s) + s * 2.3 + 0.7) * 0.62, 0.0);
}
float wellWeight(uint site, float t)
{
	return smoothstep(0.35, 0.85, 0.5 + 0.5 * sin(t * 0.075 + float(site) * 1.1));
}

vec3 baseEmitter(vec3 cur, vec3 perp, float spin)
{
	// upstream edge of the frame, wandering slowly along it
	return vec3(-cur.x * uC.z * 1.02, -cur.y * 1.02, 0.0) + perp * 0.35 * sin(spin * 0.6) + vec3(0.0, 0.0, 0.05 * sin(spin));
}

void main()
{
	ivec2 px = ivec2(gl_FragCoord.xy);
	ivec2 res = textureSize(sTD2DInputs[0], 0);
	uint id = uint(px.y * res.x + px.x);
	vec4 st = texelFetch(sTD2DInputs[0], px, 0);
	vec4 h = rnd4(id, 11u);
	vec4 h2 = rnd4(id, 23u);

	float phase = uT.x, spin = uT.y, dt = uT.z;
	float level = uA.x, low = uA.y, high = uA.w, onset = uB.x, arc = uB.z;
	float react = uL.x;
	bool dust = h.w > DUSTF;
	bool spr = !dust && h.w > SPRAYF;
	bool base = !dust && !spr && h.w > BASEF;
	bool jet = base && h2.w < uO.z;       // a small share of the base class keeps the thin upstream jet
	int slot = min(5, int(h2.x * 6.0));
	int sslot = min(3, int(h2.x * 4.0));
	float kick = uN.x;

	vec3 cur = vec3(normalize(uC.xy + vec2(1e-5)), 0.0);
	vec3 perp = vec3(-cur.y, cur.x, 0.0);
	vec3 p = st.xyz;
	float w = st.w;

	// ---- reset: dust scattered through the tank, jet particles queue up, puff particles wait for their puff
	if (uT.w > 0.5) {
		if (dust)
			fragColor = TDOutputSwizzle(vec4((h2.xyz - 0.5) * vec3(2.0 * uC.z + 0.4, 2.4, 0.8), 1.0 + 0.999 * h2.w));
		else if (jet)
			fragColor = TDOutputSwizzle(vec4(0.0, 0.0, 9.0, -h2.y * 6.0));
		else if (spr)
			fragColor = TDOutputSwizzle(vec4(0.0, 0.0, 9.0, 0.0));
		else
			fragColor = TDOutputSwizzle(vec4(0.0, 0.0, 9.0, 0.0));
		return;
	}

	// ---- dust: slow drift, wraps around the tank, never dies
	if (dust) {
		vec3 g;
		snoise(p * 1.3 + vec3(0.0, 0.0, 0.05 * phase), g);
		p += (cur * uK.y * 0.025 + g * 0.012 + vec3(0.0, 0.01 * uL.w, 0.0)) * dt * uM.y;
		vec3 box = vec3(uC.z + 0.2, 1.2, 0.4);
		p = mod(p + box, 2.0 * box) - box;
		fragColor = TDOutputSwizzle(vec4(p, w));
		return;
	}

	// ---- waiting jet particles count down to their first emission
	float gen = floor(max(w, 0.0));
	float life = max(w, 0.0) - gen;
	vec3 E = baseEmitter(cur, perp, spin);
	if (w < 0.0) {
		w += dt;
		if (w >= 0.0) {
			p = E + sph(h2.xy) * (0.07 + 0.05 * level + 0.06 * low * react) * pow(h.z, 0.33);
			w = 1.999;
		}
		fragColor = TDOutputSwizzle(vec4(p, w));
		return;
	}

	vec4 P = puff(slot);
	P.x *= uC.z;                          // to world units for this aspect ratio
	float A = puffAge(slot);
	vec4 SP = spray(sslot);
	SP.x *= uC.z;
	float SA = uSa[sslot];

	// ---- dead: the jet re-emits at once; a puff particle re-emits only during its puff's injection window
	if (life <= 0.0) {
		if (spr) {                        // a spray: a 0.12 s burst from its point
			float emitT = h2.y * 0.12;
			if (SA >= emitT && SA < emitT + 0.2) {
				p = vec3(SP.xy, 0.0) + sph(rnd4(id, uint(gen) * 17u + 5u).xy) * 0.015;
				fragColor = TDOutputSwizzle(vec4(p, gen + 1.999));
				return;
			}
			fragColor = TDOutputSwizzle(vec4(p, gen));
			return;
		}
		if (base && !jet) {               // a well: re-emit at its drifting source while it is active
			uint site = id % 6u;
			float wt = wellWeight(site, spin * 8.0);
			float rate = uO.w * wt * (0.35 + 1.1 * level * react) * 2.0;
			if (rnd4(id, uint(phase * 1000.0) + 7u).x < rate * dt) {
				vec4 j = rnd4(id, uint(gen) * 37u + 101u);
				p = wellPos(site, spin * 8.0) + sph(j.xy) * (0.035 + 0.05 * low * react) * pow(j.z, 0.33);
				fragColor = TDOutputSwizzle(vec4(p, gen + 1.999));
				return;
			}
			fragColor = TDOutputSwizzle(vec4(p, gen));
			return;
		}
		if (jet) {
			p = E + sph(rnd4(id, uint(gen) * 7u + 3u).xy) * (0.07 + 0.05 * level + 0.06 * low * react) * pow(h.z, 0.33);
			fragColor = TDOutputSwizzle(vec4(p, gen + 1.999));
			return;
		}
		float emitDur = 1.0 + 2.2 * P.w;
		float emitT = h2.y * emitDur;
		if (A >= emitT && A < emitT + 0.75) {
			vec4 j = rnd4(id, uint(gen) * 131u + 977u);
			p = vec3(P.xy, 0.0) + sph(j.xy) * (0.06 + 0.08 * P.w) * uM.x * pow(j.z, 0.33);
			fragColor = TDOutputSwizzle(vec4(p, gen + 1.999));
			return;
		}
		fragColor = TDOutputSwizzle(vec4(p, gen));        // stays dead (invisible) until its next window
		return;
	}

	float lifetime = spr ? lifeSpray(h2) : jet ? lifeBase(h2) : base ? lifeCondensed(h2) : lifePuff(h2);
	float age = (1.0 - life) * lifetime;
	vec3 vel = vec3(0.0);

	// the water drifts along the current (stronger when the music swells)
	vel += cur * uK.y * (0.05 + 0.08 * arc * react);

	if (spr) {
		// a spray droplet: shot out fast in a cone around the burst direction, braking hard -> thin streaks
		vec4 j = rnd4(id, uint(gen) * 29u + 7u);
		float a = SP.z + (j.x - 0.5) * 3.2;
		vel += vec3(cos(a), sin(a), (j.z - 0.5) * 0.3) * (0.6 + 2.2 * j.y * j.y) * SP.w * uM.w * exp(-age / 0.3);
	} else if (jet) {
		// the jet: momentum along a slowly swaying direction, decaying as the ink slows down
		float sway = 0.35 * sin(spin * 0.8 + 1.3) + 0.15 * sin(spin * 2.1);
		vec3 jd = cur * cos(sway) + perp * sin(sway);
		vel += jd * uK.z * (0.14 + 0.30 * level * react) * exp(-age / 2.5);
	} else if (base) {
		// welling ink pushes gently outwards from its source for a moment, then the water carries it
		vec3 wr = p - wellPos(id % 6u, spin * 8.0);
		vel += normalize(wr + vec3(1e-4)) * 0.06 * (0.6 + 0.8 * low * react) * exp(-age / 1.2);
	} else {
		// a puff: injected along its direction, then rolls up into a vortex ring (mushroom cap)
		vec3 dir = vec3(cos(P.z), sin(P.z), 0.0);
		vel += dir * uK.z * 0.40 * P.w * exp(-age / 1.8);
		float L = 0.45 + 0.5 * P.w;
		vec3 c = vec3(P.xy, 0.0) + dir * L * (1.0 - exp(-A / 2.2));
		float R = (0.10 + 0.12 * sqrt(A)) * uM.x * (0.7 + 0.6 * P.w);
		float G = uK.w * 1.4 * P.w * exp(-A / 7.0) * (0.7 + 0.6 * low * react);
		vec3 r = p - c;
		float along = dot(r, dir);
		vec3 rr = r - along * dir;
		float rho = length(rr) + 1e-4;
		vec3 rh = rr / rho;
		vec3 dv = (rho - R) * rh + along * dir;
		float dd = dot(dv, dv);
		vel += G * (along * rh - (rho - R) * dir) / (dd + 0.25 * R * R) * R * exp(-dd / (4.0 * R * R));
	}

	// billows: curl noise that drifts with the water and grows as the ink ages. The large octave swells with the
	// bass; the fine octave (below) belongs to the treble.
	float freq = 1.0 + 0.6 * uB.y;
	vec3 q = p * freq + vec3(0.0, 0.0, 0.07 * phase) - cur * 0.15 * phase;
	vec3 flow = curlNoise(q) * (0.45 + 0.8 * low * react * uM.z) + 0.5 * curlNoise(q * 2.2 + vec3(7.1, -3.3, 2.9));
	float turb = uK.x * (0.05 + 0.12 * smoothstep(0.0, 3.0, age)) * (0.6 + 0.6 * arc * react + 0.5 * onset * react);
	float hat = uN.z;
	if (spr) {
		// droplets wiggle in a fine, fast field that the high band stirs
		vel += curlNoise(p * 4.5 + vec3(0.0, 0.3, 0.2) * phase) * (0.05 + 0.12 * high * react);
	} else {
		vel += flow * turb;
		// BASS - a slow gyre: the whole water turns with the low band
		vec3 gr = p - vec3(0.0, 0.0, 0.0);
		vel += vec3(-gr.y, gr.x, 0.0) * low * low * react * uM.z * 0.30 * exp(-dot(gr, gr) * 0.6) * (cur.x >= 0.0 ? 1.0 : -1.0);
		// TREBLE - flutter: a fine, fast flow (independent of age, so even fresh ink trembles)
		if (uL.z > 0.001) {
			vec3 qf = p * 5.3 * freq + vec3(3.3, 1.7, -5.1) + vec3(0.2, 0.5, 0.3) * phase * (1.0 + 2.0 * high);
			vel += curlNoise(qf) * uL.z * uO.x * (0.012 + 0.07 * high * react + 0.10 * hat * react);
		}
		// TREBLE - every hi-hat flicks three small whirls into the tendrils
		for (int i = 0; i < 3; i++) {
			vec4 fr = rnd4(uint(uO.y) * 3u + uint(i), 61u);
			vec3 fd = p - vec3((fr.x - 0.5) * 1.4 * uC.z, (fr.y - 0.5) * 1.6, 0.0);
			vel += vec3(-fd.y, fd.x, 0.0) * (fr.z > 0.5 ? 1.0 : -1.0) * hat * react * uO.x * 9.0 * exp(-dot(fd, fd) / 0.02);
		}
		// BASS - low hits thump the water: a pressure wave from a random impact point pushes the ink outwards
		vec4 kr = rnd4(uint(uN.y), 13u);
		vec3 kc = vec3((kr.x - 0.5) * 1.2 * uC.z, (kr.y - 0.5) * 1.2, 0.0);
		vec3 kd = p - kc;
		float kl = length(kd) + 1e-3;
		vel += (kd / kl) * kick * uM.z * react * (0.6 + 0.6 * low) * 1.6 * exp(-kl * kl * 2.0);
	}

	vel.y += uL.w * 0.03;                 // buoyancy
	vel.z -= p.z * 0.3;                   // keep the ink near the middle of the tank
	p += vel * dt * uM.y;

	life -= dt / lifetime;
	if (abs(p.x) > uC.z + 0.7 || abs(p.y) > 1.6)
		life = 0.0;                       // left the tank
	fragColor = TDOutputSwizzle(vec4(p, gen + max(life, 0.0)));
}
