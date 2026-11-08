// Paws & Play Pet Sitting — site interactions

// ===== CONTACT & FORM SETUP =====
// Booking requests are emailed to this address.
const CONTACT_EMAIL = "pawsandplaypetsoh@gmail.com";
const CONTACT_PHONE = "(330) 690-0090";

// By default the form sends through FormSubmit (formsubmit.co), which needs no account.
// The first request triggers a one-time "Activate form" email to CONTACT_EMAIL; click it once.
// Afterwards FormSubmit gives you a private code you can paste here instead of the email,
// so the address isn't in the form code:
const FORMSUBMIT_TO = CONTACT_EMAIL;   // or e.g. "a1b2c3d4e5f6..."

// Optional: prefer Formspree instead? Paste its form ID here and it will be used instead.
const FORMSPREE_ID = "";
// ================================

// Sends a booking request to the inbox. Throws if it didn't go through.
async function sendBooking(data) {
  const useFormspree = Boolean(FORMSPREE_ID);
  const url = useFormspree
    ? `https://formspree.io/f/${encodeURIComponent(FORMSPREE_ID)}`
    : `https://formsubmit.co/ajax/${FORMSUBMIT_TO.trim()}`;
  const payload = useFormspree
    ? data
    : { ...data, _honey: data._gotcha, _template: "table", _captcha: "false" };
  if (!useFormspree) delete payload._gotcha;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  // FormSubmit reports some failures with a 200 status and success: "false"
  if (!res.ok || body.success === "false" || body.success === false) {
    throw new Error(body.message || body.errors?.map(e => e.message).join(", ") || `HTTP ${res.status}`);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];

  $("#year").textContent = new Date().getFullYear();

  // Mobile menu
  const toggle = $(".nav-toggle");
  const links = $("#nav-links");
  toggle.addEventListener("click", () => {
    const open = links.classList.toggle("open");
    toggle.setAttribute("aria-expanded", open);
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  });
  $$("a", links).forEach(a => a.addEventListener("click", () => {
    links.classList.remove("open");
    toggle.setAttribute("aria-expanded", "false");
  }));

  // Header shadow, back-to-top, active nav link
  const header = $(".site-header");
  const toTop = $(".to-top");
  const sections = $$("main section[id]");
  const navMap = Object.fromEntries($$(".nav-links a[href^='#']:not(.btn)").map(a => [a.getAttribute("href").slice(1), a]));
  const onScroll = () => {
    const y = window.scrollY;
    header.classList.toggle("scrolled", y > 10);
    toTop.classList.toggle("show", y > 600);
    let current = null;
    sections.forEach(s => { if (s.offsetTop - 120 <= y) current = s.id; });
    Object.entries(navMap).forEach(([id, a]) => a.classList.toggle("active", id === current));
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Reveal on scroll
  $$(".service, .benefit, .steps li, .faq details, .photo-wrap, .photo-stack, .gallery li, .features li, .booking-form, .addon").forEach(el => el.classList.add("reveal"));
  const revealObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add("visible");
      } else if (e.boundingClientRect.bottom <= 0) {
        // Already scrolled past (e.g. jumped via a menu link): show it right away, no animation
        e.target.classList.add("visible", "instant");
      } else {
        return;
      }
      revealObs.unobserve(e.target);
    });
  }, { threshold: 0, rootMargin: "0px 0px -8% 0px" });
  $$(".gallery li").forEach((li, i) => li.style.setProperty("--i", i % 4));
  let pendingReveal = $$(".reveal");
  pendingReveal.forEach(el => revealObs.observe(el));

  // Backup for fast scrolling: the observer can miss elements flung past between frames,
  // so on every scroll frame anything at or above the screen gets shown too.
  function sweepReveals() {
    if (!pendingReveal.length) return;
    const vh = window.innerHeight;
    pendingReveal = pendingReveal.filter(el => {
      if (el.classList.contains("visible")) return false;
      const r = el.getBoundingClientRect();
      if (r.top < vh * 0.92) {
        el.classList.add("visible");
        if (r.bottom <= 0) el.classList.add("instant");
        revealObs.unobserve(el);
        return false;
      }
      return true;
    });
  }

  // Scribble underlines draw in when their heading is on screen
  const scribbleObs = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add("drawn"); scribbleObs.unobserve(e.target); } });
  }, { threshold: 0.8 });
  let pendingScribbles = $$(".scribble");
  pendingScribbles.forEach(el => scribbleObs.observe(el));
  function sweepScribbles() {
    if (!pendingScribbles.length) return;
    const vh = window.innerHeight;
    pendingScribbles = pendingScribbles.filter(el => {
      if (el.classList.contains("drawn")) return false;
      if (el.getBoundingClientRect().top < vh * 0.85) { el.classList.add("drawn"); scribbleObs.unobserve(el); return false; }
      return true;
    });
  }

  // Scroll effects: progress bar, light parallax, paw-print trail
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const progress = $(".scroll-progress");
  const parallaxEls = $$("[data-parallax]");
  let trailPaws = [];

  function buildPawTrail() {
    $(".paw-trail")?.remove();
    trailPaws = [];
    if (reduceMotion || window.innerWidth < 1280) return;
    const trail = document.createElement("div");
    trail.className = "paw-trail";
    trail.setAttribute("aria-hidden", "true");
    const gutter = (window.innerWidth - Math.min(1150, window.innerWidth * 0.92)) / 2;
    const docH = document.documentElement.scrollHeight;
    const startY = window.innerHeight * 0.9;
    const line = window.scrollY + window.innerHeight * 0.75;
    for (let y = startY, i = 0; y < docH - 500; y += 120, i++) {
      const paw = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      // Paws already walked past stay visible when the trail is re-measured (no blinking)
      paw.setAttribute("class", y < line ? "trail-paw on" : "trail-paw");
      paw.innerHTML = '<use href="#i-paw"/>';
      const left = i % 2 === 0;
      // Walk down the left margin, gently weaving like real steps
      const x = gutter / 2 - 11 + (left ? -14 : 14) + Math.sin(i / 3) * 10;
      paw.style.left = `${x}px`;
      paw.style.top = `${y}px`;
      paw.style.rotate = `${180 + (left ? -12 : 12)}deg`;
      trail.appendChild(paw);
      trailPaws.push({ el: paw, y, on: y < line });
    }
    document.body.appendChild(trail);
  }

  let ticking = false;
  function onScrollFx() {
    ticking = false;
    const y = window.scrollY;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.setProperty("--p", max > 0 ? (y / max).toFixed(4) : 0);
    sweepReveals();
    sweepScribbles();
    if (reduceMotion) return;
    if (window.innerWidth > 700) {
      const mid = window.innerHeight / 2;
      parallaxEls.forEach(el => {
        const r = el.getBoundingClientRect();
        // Measure from the element's resting spot (minus its current shift) so it never feeds back on itself
        const prev = el._shift || 0;
        const top = r.top - prev;
        if (r.bottom - prev < -200 || top > window.innerHeight + 200) return;
        const shift = Math.round((top + r.height / 2 - mid) * parseFloat(el.dataset.parallax) * 2) / 2;
        if (shift !== prev) {
          el._shift = shift;
          el.style.translate = `0 ${shift}px`;
        }
      });
    }
    const line = y + window.innerHeight * 0.75;
    trailPaws.forEach(p => {
      const on = p.y < line;
      if (on !== p.on) { p.on = on; p.el.classList.toggle("on", on); }
    });
  }
  const requestFx = () => { if (!ticking) { ticking = true; requestAnimationFrame(onScrollFx); } };
  window.addEventListener("scroll", requestFx, { passive: true });
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { buildPawTrail(); requestFx(); }, 200);
  });
  window.addEventListener("load", () => { buildPawTrail(); requestFx(); });
  // Re-measure when the page grows (e.g. photos finish loading), at most a few times a second
  let lastH = document.documentElement.scrollHeight;
  if ("ResizeObserver" in window) {
    new ResizeObserver(() => {
      const h = document.documentElement.scrollHeight;
      if (Math.abs(h - lastH) < 40) return;
      lastH = h;
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => { buildPawTrail(); requestFx(); }, 250);
    }).observe(document.body);
  }
  buildPawTrail();
  requestFx();

  // Gallery lightbox
  const lightbox = $("#lightbox");
  const items = $$(".gallery-item");
  const lbImg = $("img", lightbox);
  const lbCap = $("figcaption", lightbox);
  let current = 0;
  const showPhoto = i => {
    current = (i + items.length) % items.length;
    const item = items[current];
    lbImg.src = item.dataset.full;
    lbImg.alt = $("img", item).alt;
    lbCap.textContent = item.dataset.caption;
  };
  items.forEach((item, i) => item.addEventListener("click", () => {
    showPhoto(i);
    if (typeof lightbox.showModal === "function") lightbox.showModal();
    else window.open(item.dataset.full, "_blank");
  }));
  $(".lb-close", lightbox).addEventListener("click", () => lightbox.close());
  $(".lb-prev", lightbox).addEventListener("click", () => showPhoto(current - 1));
  $(".lb-next", lightbox).addEventListener("click", () => showPhoto(current + 1));
  lightbox.addEventListener("click", e => { if (e.target === lightbox) lightbox.close(); });
  lightbox.addEventListener("keydown", e => {
    if (e.key === "ArrowLeft") showPhoto(current - 1);
    if (e.key === "ArrowRight") showPhoto(current + 1);
  });
  let touchX = null;
  lightbox.addEventListener("touchstart", e => { touchX = e.touches[0].clientX; }, { passive: true });
  lightbox.addEventListener("touchend", e => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 50) showPhoto(current + (dx < 0 ? 1 : -1));
    touchX = null;
  });

  // Service buttons prefill the booking form
  const form = $("#booking-form");
  $$("[data-service]").forEach(b => b.addEventListener("click", () => {
    form.elements.service.value = b.dataset.service;
    if (b.dataset.walk) form.elements.walks.checked = true;
    setTimeout(() => form.elements.name.focus({ preventScroll: true }), 600);
  }));

  // Booking form validation
  const startInput = form.elements.startDate;
  const endInput = form.elements.endDate;
  const today = new Date();
  today.setMinutes(today.getMinutes() - today.getTimezoneOffset());
  startInput.min = endInput.min = today.toISOString().split("T")[0];
  startInput.addEventListener("change", () => { endInput.min = startInput.value || startInput.min; });

  const rules = {
    name: v => v.trim().length >= 2 || "Please enter your name.",
    email: v => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) || "Please enter a valid email.",
    phone: v => v.replace(/\D/g, "").length >= 10 || "Please enter a 10-digit phone number.",
    town: v => v.trim().length >= 2 || "Which town are you in?",
    pets: v => v.trim().length >= 1 || "What are your pets' names?",
    petType: v => v !== "" || "Please choose a pet type.",
    service: v => v !== "" || "Please choose a service.",
    startDate: v => (v && v >= startInput.min) || "Please pick today or a future date.",
    endDate: v => !v || (v >= (startInput.value || startInput.min)) || "End date can't be before the start date.",
  };
  const validate = field => {
    const result = rules[field.name](field.value);
    const label = field.closest("label");
    const ok = result === true;
    label.classList.toggle("invalid", !ok);
    $(".error", label).textContent = ok ? "" : result;
    field.setAttribute("aria-invalid", !ok);
    return ok;
  };
  Object.keys(rules).forEach(n => {
    const f = form.elements[n];
    f.addEventListener("blur", () => validate(f));
    f.addEventListener("change", () => { if (f.closest("label").classList.contains("invalid")) validate(f); });
    f.addEventListener("input", () => { if (f.closest("label").classList.contains("invalid")) validate(f); });
  });

  const fmt = d => new Date(d + "T12:00").toLocaleDateString(undefined, { weekday: "short", month: "long", day: "numeric" });
  const status = $(".form-status", form);
  const submitBtn = $("button[type=submit]", form);

  form.addEventListener("submit", async e => {
    e.preventDefault();
    if (submitBtn.disabled) return;
    const fields = Object.keys(rules).map(n => form.elements[n]);
    const results = fields.map(validate);
    if (results.includes(false)) {
      fields[results.indexOf(false)].focus();
      status.className = "form-status";
      status.textContent = "Please fix the highlighted fields.";
      return;
    }
    const data = Object.fromEntries(new FormData(form));
    data.walks = data.walks ? "Yes (+$5 per visit)" : "No";
    const dates = data.endDate && data.endDate !== data.startDate ? `${fmt(data.startDate)} – ${fmt(data.endDate)}` : fmt(data.startDate);
    data._subject = `New request: ${data.service} for ${data.pets} (${data.town}), ${dates}`;
    data._replyto = data.email;

    const label = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = "Sending…";
    status.className = "form-status";
    status.textContent = "";
    try {
      await sendBooking(data);
      status.className = "form-status success";
      status.textContent = `Thanks, ${data.name.trim().split(" ")[0]}! Your ${data.service.toLowerCase()} request for ${data.pets} (${dates}) was sent. I'll be in touch at ${data.email} or ${data.phone} soon.`;
      form.reset();
      endInput.min = startInput.min;
    } catch (err) {
      console.error("Booking failed:", err);
      // Offer a ready-made email with their request so nothing is lost
      const lines = [
        `Name: ${data.name}`, `Email: ${data.email}`, `Phone: ${data.phone}`, `Town: ${data.town}`,
        `Pets: ${data.pets} (${data.petType})`, `Service: ${data.service}`, `Dates: ${dates}`,
        `Walks: ${data.walks}`, data.notes ? `Notes: ${data.notes}` : "",
      ].filter(Boolean).join("\n");
      const mailto = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(data._subject)}&body=${encodeURIComponent(lines)}`;
      const tel = "tel:+1" + CONTACT_PHONE.replace(/\D/g, "");
      status.className = "form-status fail";
      status.textContent = "Sorry, that didn't go through. Please try again, ";
      const a1 = Object.assign(document.createElement("a"), { href: mailto, textContent: `email ${CONTACT_EMAIL}` });
      const a2 = Object.assign(document.createElement("a"), { href: tel, textContent: `call ${CONTACT_PHONE}` });
      status.append(a1, " (your request is filled in), or ", a2, ".");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = label;
    }
  });
});
