import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from config import (PANEL_BG, GRID_L, TEXT, MUTED, WHITE,
                    RED, BLUE, CYAN, GREEN)

# Extra colors for new statuses
PURPLE = (180,  60, 255)
ORANGE = (220, 130,  20)
YELLOW = (220, 220,  80)


class SimPanel:
    def __init__(self, x, w, h):
        self.x=x; self.w=w; self.h=h
        self.speed        = 3
        self.dragging     = False
        self.show_bubbles = True
        self._naming      = False
        self._name_inp    = ""
        self._export_msg  = ""

        STAT_TOP  = 54
        STAT_H    = 20          # slightly smaller to fit more rows
        # 11 stat rows now
        stats_bot = STAT_TOP + 11 * STAT_H

        SPD_TOP   = stats_bot + 20
        BTN_TOP   = SPD_TOP   + 34
        BTN_H     = 28
        BTN_GAP   = 5

        self.spd_r = pygame.Rect(x+14, SPD_TOP,                      w-28, 12)
        self.rst_r = pygame.Rect(x+14, BTN_TOP,                      w-28, BTN_H)
        self.shf_r = pygame.Rect(x+14, BTN_TOP+(BTN_H+BTN_GAP),     w-28, BTN_H)
        self.new_r = pygame.Rect(x+14, BTN_TOP+(BTN_H+BTN_GAP)*2,   w-28, BTN_H)
        self.bub_r = pygame.Rect(x+14, BTN_TOP+(BTN_H+BTN_GAP)*3,   w-28, BTN_H)
        self.exp_r = pygame.Rect(x+14, BTN_TOP+(BTN_H+BTN_GAP)*4,   w-28, BTN_H)

        self._stat_top    = STAT_TOP
        self._stat_h      = STAT_H
        self._spd_label_y = SPD_TOP - 16

        self._name_r = pygame.Rect(
            x+14, self.exp_r.bottom+6, w-28, 26)

    def is_naming(self):
        return self._naming

    def handle(self, ev, sim, app):
        if self._naming:
            if ev.type == pygame.KEYDOWN:
                k = ev.key
                if k == pygame.K_RETURN:
                    path = sim.save_log(
                        custom_name=self._name_inp.strip())
                    self._export_msg = (
                        "✓ " + os.path.basename(path))
                    self._naming   = False
                    self._name_inp = ""
                elif k == pygame.K_ESCAPE:
                    self._naming     = False
                    self._name_inp   = ""
                    self._export_msg = "Cancelled"
                elif k == pygame.K_BACKSPACE:
                    self._name_inp = self._name_inp[:-1]
                elif ev.unicode and ev.unicode.isprintable():
                    if ev.unicode not in r'\/:*?"<>|':
                        self._name_inp += ev.unicode
            return

        if ev.type == pygame.MOUSEBUTTONDOWN:
            mx, my = ev.pos
            if   self.spd_r.collidepoint(mx,my):
                self.dragging = True
            elif self.rst_r.collidepoint(mx,my):
                sim.reset(); self._export_msg = ""
            elif self.shf_r.collidepoint(mx,my):
                sim.new_paths(); self._export_msg = ""
            elif self.new_r.collidepoint(mx,my):
                app.goto_setup()
            elif self.bub_r.collidepoint(mx,my):
                self.show_bubbles = not self.show_bubbles
            elif self.exp_r.collidepoint(mx,my):
                self._naming     = True
                self._name_inp   = ""
                self._export_msg = ""

        if ev.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        if ev.type == pygame.MOUSEMOTION and self.dragging:
            t = (ev.pos[0]-self.spd_r.x) / self.spd_r.w
            self.speed = int(max(1, min(10, round(t*9+1))))

    def draw(self, surf, sim, fonts):
        f_t, f_b, f_s = fonts
        pygame.draw.rect(surf, PANEL_BG,
                         (self.x,0,self.w,self.h))
        pygame.draw.line(surf, GRID_L,
                         (self.x,0),(self.x,self.h), 1)

        surf.blit(f_t.render("UTM Sim", True, TEXT),
                  (self.x+12, 10))
        surf.blit(f_s.render("Traffic Monitor", True, MUTED),
                  (self.x+12, 28))

        # ── KPI stats ─────────────────────────────────────────────────────
        active,waiting,arrived,crashed,direct,prox = sim.stats()

        # Count each status individually
        n_arrived   = sum(1 for d in sim.drones
                          if d.status == "arrived")
        n_direct    = sum(1 for d in sim.drones
                          if d.status == "crashed_direct")
        n_prox      = sum(1 for d in sim.drones
                          if d.status == "crashed_prox")
        n_battery   = sum(1 for d in sim.drones
                          if d.status == "incomplete_battery")
        n_cncl_pre  = sum(1 for d in sim.drones
                          if d.status == "cancelled"
                          and d.cancel_reason == "pre_flight")
        n_cncl_mid  = sum(1 for d in sim.drones
                          if d.status == "cancelled"
                          and d.cancel_reason == "in_flight")
        n_waiting   = sum(1 for d in sim.drones
                          if d.status == "waiting")
        n_active    = sum(1 for d in sim.drones
                          if d.status == "active")

        rows = [
            # label          value          color
            ("Active",        str(n_active),   CYAN),
            ("Waiting",       str(n_waiting),  MUTED),
            ("Arrived",       str(n_arrived),  GREEN),
            ("Crash Direct",  str(n_direct),   RED),
            ("Crash Prox",    str(n_prox),     BLUE),
            ("Battery Dead",  str(n_battery),  PURPLE),
            ("Cncl Pre-flt",  str(n_cncl_pre), YELLOW),
            ("Cncl In-flt",   str(n_cncl_mid), ORANGE),
            ("Near Miss",     str(sim.nearmiss_count), (200,200,80)),
            ("Tick",          str(sim.grid_tick),      MUTED),
            ("Drones",        str(len(sim.drones)),    TEXT),
        ]

        for i, (nm, vl, col) in enumerate(rows):
            y  = self._stat_top + i * self._stat_h
            bg = (20,28,50) if i%2==0 else (16,22,42)
            pygame.draw.rect(surf, bg,
                             (self.x+8, y,
                              self.w-16,
                              self._stat_h-2),
                             border_radius=3)
            surf.blit(f_s.render(nm, True, MUTED),
                      (self.x+12, y+3))
            v = f_s.render(vl, True, col)
            surf.blit(v,
                      (self.x+self.w-12-v.get_width(),
                       y+3))

        # ── Speed slider ──────────────────────────────────────────────────
        ly = self._spd_label_y
        surf.blit(f_s.render("Speed", True, MUTED),
                  (self.spd_r.x, ly))
        sv = f_s.render(str(self.speed), True, TEXT)
        surf.blit(sv,
                  (self.spd_r.right-sv.get_width(), ly))
        pygame.draw.rect(surf,(32,42,72),
                         self.spd_r, border_radius=4)
        t2 = (self.speed-1)/9
        pygame.draw.rect(surf,(55,115,210),
            pygame.Rect(self.spd_r.x, self.spd_r.y,
                        int(self.spd_r.w*t2),
                        self.spd_r.h),
            border_radius=4)
        tx = self.spd_r.x+int(self.spd_r.w*t2)
        pygame.draw.circle(surf, WHITE,
                           (tx, self.spd_r.y+6), 7)
        pygame.draw.circle(surf,(55,115,210),
                           (tx, self.spd_r.y+6), 6)

        # ── Buttons ───────────────────────────────────────────────────────
        mouse = pygame.mouse.get_pos()
        for r, label in [
            (self.rst_r, "↺  Same paths"),
            (self.shf_r, "⟳  Next ranked path"),
            (self.new_r, "＋  New drone setup"),
            (self.bub_r, "◉  Bubbles" if self.show_bubbles
                         else "○  Bubbles"),
            (self.exp_r, "⬇  Export Excel"),
        ]:
            hov = r.collidepoint(mouse)
            if r is self.exp_r and self._naming:
                bg_col = (55,80,130)
            else:
                bg_col = (38,54,90) if hov else (26,36,66)
            pygame.draw.rect(surf, bg_col,
                             r, border_radius=5)
            pygame.draw.rect(surf,(62,90,148),
                             r, 1, border_radius=5)
            lb = f_s.render(label, True, TEXT)
            surf.blit(lb,
                      (r.x+r.w//2-lb.get_width()//2,
                       r.y+r.h//2-lb.get_height()//2))

        # ── Name input box ────────────────────────────────────────────────
        if self._naming:
            pygame.draw.rect(surf,(22,29,54),
                             self._name_r, border_radius=4)
            pygame.draw.rect(surf,(65,140,220),
                             self._name_r, 1, border_radius=4)
            cur  = "|" if (pygame.time.get_ticks()//500)%2==0 \
                   else " "
            disp = (self._name_inp[-16:]
                    if len(self._name_inp)>16
                    else self._name_inp)
            surf.blit(f_s.render(disp+cur, True, WHITE),
                      (self._name_r.x+6,
                       self._name_r.y+6))
            hy = self._name_r.bottom+4
            surf.blit(f_s.render(
                "Name (blank=trial_run_N)",
                True, MUTED),(self.x+14, hy)); hy+=14
            surf.blit(f_s.render(
                "Enter=save  Esc=cancel",
                True, MUTED),(self.x+14, hy))

        elif self._export_msg:
            surf.blit(f_s.render(
                self._export_msg, True,
                GREEN if self._export_msg.startswith("✓")
                else MUTED),
                (self.exp_r.x, self._name_r.y+6))

        # ── Legend ────────────────────────────────────────────────────────
        leg_y = self._name_r.bottom + 32
        surf.blit(f_s.render("Legend", True, MUTED),
                  (self.x+12, leg_y)); leg_y += 16

        legend_items = [
            ("● Active",          CYAN),
            ("✖ Direct collision", RED),
            ("⚠ Prox collision",   BLUE),
            ("⚡ Battery dead",     PURPLE),
            ("P Pre-flt cancel",   YELLOW),
            ("I In-flt cancel",    ORANGE),
            ("● Arrived",          GREEN),
        ]
        for txt, col in legend_items:
            surf.blit(f_s.render(txt, True, col),
                      (self.x+12, leg_y))
            leg_y += 15

        # ── Keyboard hints ────────────────────────────────────────────────
        hint_y = self.h - 34
        for line in ["SPC pause  R reset",
                     "N setup   P paths"]:
            l = f_s.render(line, True, MUTED)
            surf.blit(l,(self.x+12, hint_y))
            hint_y += 14