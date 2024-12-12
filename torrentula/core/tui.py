import curses
from .peer import Peer
from ..utils.helpers import logger
import math

LEFT_INDENT = 2


class Tui:
    def __init__(self, client, stdscr=None):
        if not stdscr:  # Occurs when '--tui' command line argument is not provided.
            self.active = False
            return

        self.win = stdscr
        self.active = True
        self.client = client
        # Calculate column positions from column widths
        self.column_widths = (17, 10, 20, 11, 11, 18, 15, 15, 11, 16, 15, 9, 10)
        total = LEFT_INDENT  # Initial indent
        self.columns = []
        for width in self.column_widths:
            self.columns.append(total)
            total += width

        curses.curs_set(0)  # Hide the cursor
        self.win.nodelay(True)  # Non-blocking input

        self.MIN_X = self.columns[-1] + self.column_widths[-1] + 2
        self.MIN_Y = 14

    def draw_header(self, row):
        hdr = Peer.display_headers()
        self.win.hline(row, LEFT_INDENT, "-", self.columns[-1] + self.column_widths[-1])
        for col, width in zip(hdr, self.columns):
            self.win.addstr(row + 1, width, "| " + col)
        self.win.addstr(row + 1, self.columns[-1] + self.column_widths[-1] + 1, "|")
        self.win.hline(row + 2, LEFT_INDENT, "-", self.columns[-1] + self.column_widths[-1])
        return row + 3

    def update_display(self, summary_method):
        if not self.active:
            return
        # Gracefully handle insufficiently large terminal.
        if self.win.getmaxyx()[0] < self.MIN_Y or self.win.getmaxyx()[1] < self.MIN_X:
            logger.critical("Display requires larger terminal screen size.")
            curses.endwin()
            self.active = False
            return

        self.win.noutrefresh()
        row = 0
        summary = summary_method()

        # Piece visualization
        self.win.hline(row, LEFT_INDENT, "-", len(summary) + 4)
        row += 1
        title = "| Torrentula |"
        self.win.addstr(row, LEFT_INDENT, title + self.display_bitfield_progress(len(summary) - len(title) + 3) + "|")
        row += 1
        self.win.hline(row, LEFT_INDENT, "-", len(summary) + 4)
        row += 1
        row += 1

        # Summary row
        self.win.hline(row, LEFT_INDENT, "-", len(summary) + 4)
        row += 1
        self.win.addstr(row, LEFT_INDENT, "| " + summary + " |")
        row += 1
        self.win.hline(row, LEFT_INDENT, "-", len(summary) + 4)
        row += 1
        row += 1

        # Peer display
        peers = self.fetch_peer_data()
        row = self.draw_header(row)
        max_peers = min(self.win.getmaxyx()[0] - row - 1, len(peers))
        for i, peer in enumerate(peers[: max_peers]):
            for j, (col, width) in enumerate(zip(peer, self.columns)):
                self.win.addstr(row + i, width, f"| {col}".ljust(self.column_widths[j]))
            self.win.addstr(row + i, self.columns[-1] + self.column_widths[-1], " |")
        self.win.hline(row + max_peers, LEFT_INDENT, "-", self.columns[-1] + self.column_widths[-1])

        # Handle input
        key = self.win.getch()
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
        if l > p:  # Handle unusual case when l is greater than length of bitfield
            res = [" "] * l
            for i in range(l):
                if bitfield[math.floor(i / l * p)] == 1:
                    res[i] = "#"
        else:
            res = [" "] * l
            THRESHOLD = 0.75
            for i in range(l):
                j_start = math.floor(i / l * p)
                j_end = math.ceil((i + 1) / l * p)
                if sum(bitfield[j_start:j_end]) / (j_end - j_start + 1) > THRESHOLD:
                    res[i] = "#"
        return "".join(res)
