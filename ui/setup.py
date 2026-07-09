import random
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from config import (GRID_UNITS, STEP, CELLS, BG, GRID_L, TEXT,
                    MUTED, WHITE, RED, GREEN, DRONE_COLORS,
                    DEFAULT_DRONE_SPEED, DEFAULT_BATTERY)
from grid import gx, gy

VALID_VEHICLES = ["quad","hexa","octa","vtol","fixed_wing"]


class SetupScreen:
    VALID = set(range(0, GRID_UNITS + 1, STEP))

    def __init__(self, fonts):
        self.fonts        = fonts
        self.stage        = "mode_select"
        self.mode         = None
        self.file_inp     = ""
        self.file_err     = ""
        self.file_ok_msg  = ""
        self.total        = 0
        self.manual_count = 0
        self.cur_idx      = 0
        self.inp          = ""
        self.err          = ""
        self.configs      = []

    def done(self):
        return self.stage == "done"

    def handle(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        if self.stage == "mode_select":
            if ev.unicode == "1":
                self.mode  = "file"
                self.stage = "file_path"
            elif ev.unicode == "2":
                self.mode  = "manual"
                self.stage = "total"
            return
        if self.mode == "file":
            self._handle_file(ev)
        else:
            self._handle_manual(ev)

    def _handle_file(self, ev):
        k = ev.key
        if k == pygame.K_BACKSPACE:
            self.file_inp = self.file_inp[:-1]
            self.file_err = ""; self.file_ok_msg = ""
            return
        if k == pygame.K_RETURN:
            self._commit_file(); return
        if k == pygame.K_v and (pygame.key.get_mods()
                                 & pygame.KMOD_CTRL):
            try:
                pasted = pygame.scrap.get_text()
                if pasted:
                    pasted = (pasted.replace("\x00","")
                              .replace("\r","")
                              .replace("\n","").strip())
                    self.file_inp += pasted
                    self.file_err = ""; self.file_ok_msg = ""
            except Exception:
                try:
                    import pyperclip
                    pasted = pyperclip.paste().strip()
                    if pasted:
                        self.file_inp += pasted
                        self.file_err = ""
                        self.file_ok_msg = ""
                except Exception:
                    self.file_err = (
                        "Paste failed — pip install pyperclip")
            return
        if k == pygame.K_a and (pygame.key.get_mods()
                                  & pygame.KMOD_CTRL):
            self.file_inp = ""
            self.file_err = ""; self.file_ok_msg = ""
            return
        if k == pygame.K_t and self.file_inp == "":
            try:
                from file_loader import create_template
                path = create_template()
                self.file_ok_msg = (
                    f"Template written: "
                    f"{os.path.basename(path)}")
            except Exception as e:
                self.file_err = str(e)
            return
        if ev.unicode and ev.unicode.isprintable():
            self.file_inp += ev.unicode
            self.file_err = ""; self.file_ok_msg = ""

    def _handle_manual(self, ev):
        k = ev.key
        if k == pygame.K_BACKSPACE:
            self.inp = self.inp[:-1]; self.err = ""; return
        if k == pygame.K_RETURN:
            self._commit_manual(); return
        if ev.unicode and ev.unicode.isprintable():
            self.inp += ev.unicode; self.err = ""

    def _commit_file(self):
        from file_loader import load_file, validate_file
        path = self.file_inp.strip().strip('"').strip("'")
        valid, msg, preview = validate_file(path)
        if not valid:
            self.file_err = msg; return
        try:
            self.configs     = load_file(path)
            self.file_ok_msg = msg
            self.stage       = "done"
        except Exception as e:
            self.file_err = str(e)

    def _commit_manual(self):
        raw = self.inp.strip()

        if self.stage == "total":
            try:
                n = int(raw)
                if not 1 <= n <= 100: raise ValueError
                self.total = n
                self.stage = "manual_count"
                self.inp   = ""
            except ValueError:
                self.err = "Enter 1–100"

        elif self.stage == "manual_count":
            try:
                m = int(raw)
                if not 0 <= m <= self.total: raise ValueError
                self.manual_count = m
                if m == 0:
                    self._fill_auto(self.total)
                    self.stage = "done"
                else:
                    self.stage = "drones"
                self.inp = ""
            except ValueError:
                self.err = f"Enter 0–{self.total}"

        elif self.stage == "drones":
            try:
                # Format: sx,sy,dx,dy[,speed[,battery[,vehicle]]]
                parts = [p.strip() for p in raw.split(",")]
                if len(parts) < 4:
                    raise ValueError(
                        "Enter: sx,sy,dx,dy"
                        " [,speed[,battery[,vehicle]]]")

                sx = int(parts[0]); sy = int(parts[1])
                dx = int(parts[2]); dy = int(parts[3])
                for v in (sx,sy,dx,dy):
                    if v not in self.VALID:
                        raise ValueError(
                            "Coords must be multiples "
                            "of 5 (0–50)")
                if (sx,sy)==(dx,dy):
                    raise ValueError(
                        "Source must differ from destination")

                speed = DEFAULT_DRONE_SPEED
                if len(parts) >= 5 and parts[4] != "":
                    speed = float(parts[4])
                    if not 0.1 <= speed <= 5.0:
                        raise ValueError(
                            "Speed must be 0.1–5.0")

                battery = DEFAULT_BATTERY
                if len(parts) >= 6 and parts[5] != "":
                    battery = float(parts[5])
                    if not 0.0 <= battery <= 100.0:
                        raise ValueError(
                            "Battery must be 0–100")

                vehicle = "quad"
                if len(parts) >= 7 and parts[6] != "":
                    v = parts[6].lower()
                    if v not in VALID_VEHICLES:
                        raise ValueError(
                            f"Vehicle: "
                            f"{'/'.join(VALID_VEHICLES)}")
                    vehicle = v

                self.configs.append({
                    "src"          : (sx, sy),
                    "dst"          : (dx, dy),
                    "speed_mult"   : speed,
                    "battery_start": battery,
                    "vehicle_type" : vehicle,
                })
                self.cur_idx += 1
                self.inp = ""
                if self.cur_idx >= self.manual_count:
                    self._fill_auto(
                        self.total - self.manual_count)
                    self.stage = "done"
            except ValueError as e:
                self.err = str(e)

    def _fill_auto(self, count):
        nodes = [(x,y)
                 for x in range(0, GRID_UNITS+1, STEP)
                 for y in range(0, GRID_UNITS+1, STEP)]
        vehicles = ["quad","hexa","octa","vtol","fixed_wing"]
        for _ in range(count):
            s = random.choice(nodes)
            d = random.choice(nodes)
            while d == s: d = random.choice(nodes)
            self.configs.append({
                "src"          : s,
                "dst"          : d,
                "speed_mult"   : DEFAULT_DRONE_SPEED,
                "battery_start": DEFAULT_BATTERY,
                "vehicle_type" : random.choice(vehicles),
            })

    def draw(self, surf, WIDTH, HEIGHT):
        f_t,f_b,f_s = self.fonts
        surf.fill(BG)
        t = f_t.render(
            "UTM Drone Simulator — Setup", True, TEXT)
        surf.blit(t,(WIDTH//2-t.get_width()//2,28))
        if self.stage == "mode_select":
            self._draw_mode_select(surf,WIDTH,HEIGHT)
        elif self.mode == "file":
            self._draw_file(surf,WIDTH,HEIGHT)
        else:
            self._draw_manual(surf,WIDTH,HEIGHT)
        pygame.display.flip()

    def _draw_mode_select(self, surf, WIDTH, HEIGHT):
        f_t,f_b,f_s = self.fonts
        cx = WIDTH//2
        surf.blit(f_b.render("Choose input mode:",
                             True,TEXT),(cx-120,95))
        card_w,card_h = 280,150
        c1x,c1y = cx-card_w-16,130
        pygame.draw.rect(surf,(20,30,58),
                         (c1x,c1y,card_w,card_h),
                         border_radius=8)
        pygame.draw.rect(surf,(65,95,170),
                         (c1x,c1y,card_w,card_h),
                         1,border_radius=8)
        surf.blit(f_t.render("1  Import File",
                             True,DRONE_COLORS[0]),
                  (c1x+18,c1y+16))
        for i,line in enumerate([
            "Load drones from .xlsx or .csv",
            "Columns: src_x src_y dst_x dst_y",
            "speed battery_start vehicle_type",
            "Blank cells auto-filled.",
            "Press T to generate template.",
        ]):
            surf.blit(f_s.render(line,True,MUTED),
                      (c1x+18,c1y+44+i*18))

        c2x,c2y = cx+16,130
        pygame.draw.rect(surf,(20,30,58),
                         (c2x,c2y,card_w,card_h),
                         border_radius=8)
        pygame.draw.rect(surf,(65,95,170),
                         (c2x,c2y,card_w,card_h),
                         1,border_radius=8)
        surf.blit(f_t.render("2  Manual Entry",
                             True,DRONE_COLORS[1]),
                  (c2x+18,c2y+16))
        for i,line in enumerate([
            "sx,sy,dx,dy",
            "[,speed[,battery[,vehicle]]]",
            "Vehicles: quad hexa octa",
            "         vtol fixed_wing",
            "Unspecified = default values",
        ]):
            surf.blit(f_s.render(line,True,MUTED),
                      (c2x+18,c2y+44+i*18))

        surf.blit(f_s.render(
            "Press  1  or  2  to continue",
            True,MUTED),(cx-110,322))

    def _draw_file(self, surf, WIDTH, HEIGHT):
        f_t,f_b,f_s = self.fonts; lx=50
        self._mini_grid(surf,530,75,370)
        self._draw_mini_drones(surf,530,75,370)
        y=85
        for line in [
            "Import Excel or CSV File","",
            "Paste or type the full path to your file.",
            f"Defaults: speed={DEFAULT_DRONE_SPEED}×  "
            f"battery={DEFAULT_BATTERY}%  vehicle=quad",
            "","Columns (all optional):",
            "  src_x  src_y  dst_x  dst_y  "
            "speed  battery_start  vehicle_type",
        ]:
            c = TEXT if line and not line.startswith(" ") \
                else MUTED
            surf.blit(f_b.render(line,True,c),(lx,y)); y+=22

        bx,by = lx,HEIGHT-175
        pygame.draw.rect(surf,(22,29,54),
                         (bx,by,440,42),border_radius=6)
        pygame.draw.rect(surf,(65,95,170),
                         (bx,by,440,42),1,border_radius=6)
        cur = "|" if (pygame.time.get_ticks()//500)%2==0 \
              else " "
        disp = (self.file_inp[-55:]
                if len(self.file_inp)>55
                else self.file_inp)
        surf.blit(f_b.render(disp+cur,True,WHITE),
                  (bx+10,by+11))
        if self.file_err:
            surf.blit(f_s.render(self.file_err,True,RED),
                      (bx,by+50))
        elif self.file_ok_msg:
            surf.blit(f_s.render(self.file_ok_msg,
                                 True,GREEN),(bx,by+50))
        else:
            surf.blit(f_s.render(
                "Enter to load  |  Ctrl+V to paste path",
                True,MUTED),(bx,by+50))
        surf.blit(f_s.render(
            "T (empty input) — generate drone_template.xlsx",
            True,MUTED),(lx,HEIGHT-110))

    def _draw_manual(self, surf, WIDTH, HEIGHT):
        f_t,f_b,f_s = self.fonts; lx=36
        self._mini_grid(surf,530,75,370)
        self._draw_mini_drones(surf,530,75,370)
        prompts = {
            "total"        : ["Step 1 of 3","",
                              "Total drones? (1–100)"],
            "manual_count" : ["Step 2 of 3","",
                              f"Total: {self.total}",
                              "How many to define manually?",
                              f"(0–{self.total})"],
            "drones"       : [
                "Step 3 of 3","",
                f"Drone {self.cur_idx+1} of "
                f"{self.manual_count}",
                "Format:  sx,sy,dx,dy"
                "[,speed[,battery[,vehicle]]]","",
                f"Defaults: speed={DEFAULT_DRONE_SPEED}×  "
                f"battery={DEFAULT_BATTERY}%",
                "Vehicles: quad hexa octa vtol fixed_wing","",
                "Examples:",
                "  0,0,50,50",
                "  0,0,50,50,1.5",
                "  0,0,50,50,1.5,80",
                "  0,0,50,50,1.5,80,vtol",
            ],
        }
        y=90
        for line in prompts.get(self.stage,[]):
            c=(MUTED if (not line
                         or line.startswith(" ")
                         or line.startswith("("))
               else TEXT)
            surf.blit(f_b.render(line,True,c),(lx,y)); y+=20

        if self.configs:
            y+=4
            surf.blit(f_s.render("Configured:",
                                 True,MUTED),(lx,y)); y+=16
            for idx,cfg in enumerate(self.configs):
                col = DRONE_COLORS[idx%len(DRONE_COLORS)]
                s,d = cfg["src"],cfg["dst"]
                spd = cfg.get("speed_mult",
                              DEFAULT_DRONE_SPEED)
                bat = cfg.get("battery_start",
                              DEFAULT_BATTERY)
                vt  = cfg.get("vehicle_type","quad")
                mark=(" (manual)"
                      if idx<self.manual_count
                      else " (auto)")
                surf.blit(f_s.render(
                    f"  D{idx} {s}→{d} "
                    f"×{spd:.1f} B{bat:.0f}% "
                    f"{vt}{mark}",
                    True,col),(lx,y)); y+=16
                if y>HEIGHT-130: break

        bx,by = lx,HEIGHT-130
        pygame.draw.rect(surf,(22,29,54),
                         (bx,by,430,42),border_radius=6)
        pygame.draw.rect(surf,(65,95,170),
                         (bx,by,430,42),1,border_radius=6)
        cur="|" if (pygame.time.get_ticks()//500)%2==0 \
            else " "
        surf.blit(f_b.render(self.inp+cur,True,WHITE),
                  (bx+10,by+11))
        if self.err:
            surf.blit(f_s.render(self.err,True,RED),
                      (bx,by+48))
        else:
            surf.blit(f_s.render("Enter to confirm",
                                 True,MUTED),(bx,by+48))

    def _draw_mini_drones(self, surf, ox, oy, size):
        inn=size-36; sp=inn/CELLS
        mgx=lambda v: ox+18+int((v/STEP)*sp)
        mgy=lambda v: oy+18+int(((GRID_UNITS-v)/STEP)*sp)
        f_s=self.fonts[2]
        for idx,cfg in enumerate(self.configs):
            col=DRONE_COLORS[idx%len(DRONE_COLORS)]
            src,dst=cfg["src"],cfg["dst"]
            pygame.draw.circle(surf,col,
                               (mgx(src[0]),mgy(src[1])),5)
            pygame.draw.circle(surf,WHITE,
                               (mgx(src[0]),mgy(src[1])),5,1)
            dx2,dy2=mgx(dst[0]),mgy(dst[1])
            pygame.draw.line(surf,col,
                             (dx2-5,dy2-5),(dx2+5,dy2+5),2)
            pygame.draw.line(surf,col,
                             (dx2+5,dy2-5),(dx2-5,dy2+5),2)
            surf.blit(f_s.render(f"D{idx}",True,col),
                      (mgx(src[0])+6,mgy(src[1])-7))

    def _mini_grid(self, surf, ox, oy, size):
        inn=size-36; sp=inn/CELLS
        for i in range(CELLS+1):
            xi=ox+18+int(i*sp); yi=oy+18+int(i*sp)
            pygame.draw.line(surf,GRID_L,
                             (xi,oy+18),(xi,oy+18+inn),1)
            pygame.draw.line(surf,GRID_L,
                             (ox+18,yi),(ox+18+inn,yi),1)
        f=self.fonts[2]
        for i in range(0,CELLS+1,2):
            xi=ox+18+int(i*sp)
            yi=oy+18+int((CELLS-i)*sp)
            l=f.render(str(i*STEP),True,MUTED)
            surf.blit(l,(xi-7,oy+size-16))
            surf.blit(l,(ox+1,yi-6))