import curses
import time
from .peer import Peer
import sys
from ..utils.helpers import logger

LEFT_INDENT = 2

import curses
import time
import math
from .peer import Peer
import sys

LEFT_INDENT = 2

class Tui:
    def __init__(self, client, stdscr=None):
        if not stdscr:
            self.active = False
            return
        self.active = True
        self.client = client
        # self.header_widths = (17, 10, 20, 35, 15, 15, 20, 17, 8, 9)
        self.header_widths = (17, 10, 20, 35, 16, 18, 24, 22, 9, 12)
        self.columns = []
        total = LEFT_INDENT  # Initial indent
        for width in self.header_widths:
            self.columns.append(total)
            total += width

        curses.curs_set(0)  # Hide the cursor
        stdscr.nodelay(True)  # Non-blocking input
        stdscr.timeout(1000)  # Refresh rate in ms

        self.MIN_X = self.columns[-1] + self.header_widths[-1] + 2
        self.MIN_Y = 14

    def draw_header(self, win, row):
        hdr = Peer.display_headers()
        win.hline(row, LEFT_INDENT, "-", self.columns[-1] + self.header_widths[-1])
        for col, width in zip(hdr, self.columns):
            win.addstr(row + 1, width, "| " + col, curses.A_BOLD)
        win.addstr(row + 1, self.columns[-1] + self.header_widths[-1] + 1, "|", curses.A_BOLD)
        win.hline(row + 2, LEFT_INDENT, "-", self.columns[-1] + self.header_widths[-1])
        return row + 3

    def update_display(self, win):
        if not self.active:
            return
        if win.getmaxyx()[0] < self.MIN_Y or win.getmaxyx()[1] < self.MIN_X:
            logger.critical("Display requires larger terminal screen size.")
            curses.endwin()
            self.active = False
            return

        win.clear()
        row = 0
        summary = self.client.progress()

        # Piece visualization
        win.hline(row, LEFT_INDENT, "-", len(summary) + 4)
        row += 1
        title = "| Torrentula |"
        win.addstr(row, LEFT_INDENT, title + self.display_bitfield_progress(len(summary) - len(title) + 3) + "|")
        row += 1
        win.hline(row, LEFT_INDENT, "-", len(summary) + 4)
        row += 1
        row += 1

        # Summary row
        win.hline(row, LEFT_INDENT, "-", len(summary) + 4)
        row += 1
        win.addstr(row, LEFT_INDENT, "| " + summary + " |")
        row += 1
        win.hline(row, LEFT_INDENT, "-", len(summary) + 4)
        row += 1
        row += 1

        # Peer display
        peers = self.fetch_peer_data()
        row = self.draw_header(win, row)
        max_peers = min(win.getmaxyx()[0] - row - 1, len(peers))
        for i, peer in enumerate(peers[:max_peers]):
            # breakpoint()
            for col, width in zip(peer, self.columns):
                win.addstr(row + i, width, "| " + str(col))
            win.addstr(row + i, self.columns[-1] + self.header_widths[-1], " |")
        win.hline(row + max_peers - 1, LEFT_INDENT, "-", self.columns[-1] + self.header_widths[-1])

        # Handle input
        key = win.getch()
        if key == ord("q"):  # Quit on 'q'
            curses.endwin()
            self.active = False

    # Simulated peer data fetcher
    def fetch_peer_data(self):
        peers = [peer.display_peer() for peer in self.client.peers]
        # return sorted(peers, key=lambda p: p[5], reverse=True)
        return peers

    def display_bitfield_progress(self, l):
        # Map completed pieces from bitfield to length of a progress bar
        bitfield = self.client.file.bitfield
        p = len(bitfield)
        res = [" "] * l
        SCALE = 0.25
        THRESHOLD = 0.5 + SCALE * (self.client.file.total_downloaded_percentage() / 100)
        for i in range(l):
            j_start = math.floor(i / l * p)
            j_end = math.ceil((i + 1) / l * p)
            if sum(bitfield[j_start:j_end]) / (j_end - j_start + 1) > THRESHOLD:
                res[i] = "#"
        return "".join(res)
