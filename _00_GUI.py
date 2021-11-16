import tkinter as tk
from queue import Empty
from os import path
import sys
from signal import signal,\
    SIGINT
from threading import Thread
from tkinter.scrolledtext import Text, Scrollbar
from tkinter import tix, simpledialog
from tkinter import ttk, N, S, E, W, END, Label, NONE

from _00_base import configure_logger_and_queue
from _00_back_end import LEAF_back_end,\
    configuration

class ConsoleUi(configure_logger_and_queue):
    """Poll messages from a logging queue and display them in a scrolled text widget"""

    def __init__(self, frame):

        super(ConsoleUi, self).__init__()

        self.frame = frame

        # add a button to clear the text
        self.button_clear_console = ttk.Button(self.frame, text='CLEAR CONSOLE', command=self.clear_console)
        self.button_clear_console.grid(column=0, row=0, sticky=W)
        self.tip_clear_console = tix.Balloon(self.frame)
        self.tip_clear_console.bind_widget(self.button_clear_console,balloonmsg="Will clear the text from the console frame.")

        # Create a ScrolledText wdiget
        self.h_scroll = Scrollbar(self.frame, orient='horizontal')
        self.h_scroll.grid(row=2, column=0, sticky=(W, E))
        self.v_scroll = Scrollbar(self.frame, orient='vertical')
        self.v_scroll.grid(row=1, column=1, sticky=(N, S))

        self.scrolled_text = Text(frame, state='disabled', width=200, height=25, wrap=NONE, xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.scrolled_text.grid(row=1, column=0, sticky=(N, S, W, E))
        self.scrolled_text.configure(font='TkFixedFont')
        self.scrolled_text.tag_config('INFO', foreground='black')
        self.scrolled_text.tag_config('DEBUG', foreground='gray')
        self.scrolled_text.tag_config('WARNING', foreground='orange')
        self.scrolled_text.tag_config('ERROR', foreground='red')
        self.scrolled_text.tag_config('CRITICAL', foreground='red', underline=1)

        self.h_scroll.config(command=self.scrolled_text.xview)
        self.v_scroll.config(command=self.scrolled_text.yview)

        # Start polling messages from the queue
        self.frame.after(100, self.poll_log_queue)

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state='normal')
        self.scrolled_text.insert(tk.END, msg + '\n', record.levelname)
        self.scrolled_text.configure(state='disabled')

        # Autoscroll to the bottom
        self.scrolled_text.yview(tk.END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except Empty:
                break
            else:
                self.display(record)
        self.frame.after(100, self.poll_log_queue)

    def clear_console(self):
        self.scrolled_text.configure(state='normal')
        self.scrolled_text.delete('1.0', END)
        self.scrolled_text.configure(state='disabled')

class FormControls(LEAF_back_end,
                   configure_logger_and_queue
                   ):

    def __init__(self,
                 frame):
        super(FormControls, self).__init__()

        self.frame = frame

        self.label_coin_to_use = Label(self.frame, text='Coin to be used:')
        self.coin_to_use = tk.StringVar()
        self.combobox_coin_to_use = ttk.Combobox(
            self.frame,
            textvariable=self.coin_to_use,
            width=15,
            state='readonly',
            values=list(configuration.keys())
        )
        self.combobox_coin_to_use.bind("<<ComboboxSelected>>")
        self.combobox_coin_to_use.set('SELECT A COIN')
        self.label_coin_to_use.grid(column=0, row=1)
        self.combobox_coin_to_use.grid(column=0, row=2)

        self.separator_filtering = ttk.Separator(self.frame, orient='horizontal')
        self.separator_filtering.grid(column=0, row=3, sticky=(W, E), pady=10)

        self.label_hover_hints = Label(self.frame, text='NOTE: Hover on the buttons below for more info.')
        self.label_hover_hints.grid(column=0, row=4)

        self.button_display_stored_results = ttk.Button(self.frame, text='Display plot checks', command=self.master_display_stored_results)
        self.button_display_stored_results.grid(column=0, row=5, sticky=W)
        self.tip_display_stored_results = tix.Balloon(self.frame)
        self.tip_display_stored_results.bind_widget(self.button_display_stored_results,balloonmsg="Will display the plot check results for all the plots that are in the coin's config.yaml "
                                                                                                  "AND that were checked with this tool in the past")

        self.button_display_raw_output = ttk.Button(self.frame, text='Display raw output', command=self.master_display_raw_output)
        self.button_display_raw_output.grid(column=0, row=7, sticky=W)
        self.tip_display_raw_output = tix.Balloon(self.frame)
        self.tip_display_raw_output.bind_widget(self.button_display_raw_output,balloonmsg="Will display the raw output from the plot check command. Usefull for debugging.")

        self.button_check_plots = ttk.Button(self.frame, text='Check plots', command=self.master_check_plots)
        self.button_check_plots.grid(column=0, row=9, sticky=W)
        self.tip_check_plots = tix.Balloon(self.frame)
        self.tip_check_plots.bind_widget(self.button_check_plots,balloonmsg="Will begin the plots check using the coin selected above.")

    def check_coin_selection(self):
        if self.coin_to_use.get() == 'SELECT A COIN':
            self._log.warning('Please select a coin !')
            return False
        return True

    def master_display_stored_results(self):
        if self.check_coin_selection() and self.precheck_duplicates(self.coin_to_use.get()):
            self.print_stored_results(coin=self.coin_to_use.get())

    def master_display_raw_output(self):
        if self.check_coin_selection() and self.precheck_duplicates(self.coin_to_use.get()):
            self.print_raw_output(coin=self.coin_to_use.get(),
                                  filter_string=simpledialog.askstring(title="Input Required",
                                                                       prompt="Please input the name of the plot for which you want to display the raw output:"))

    def master_check_plots(self):
        if self.check_coin_selection() and self.precheck_duplicates(self.coin_to_use.get()):
            def action():
                self.combobox_coin_to_use.configure(state='disabled')
                self.button_display_stored_results.configure(state='disabled')
                self.button_display_raw_output.configure(state='disabled')
                self.button_check_plots.configure(state='disabled')
                self._log.info('Checking the plots. Controls are now disabled until the operation is done. Please wait ...')
                self.check_plots(coin=self.coin_to_use.get())
                self._log.info('Plots check completed ! Controls are now enabled.')
                self.combobox_coin_to_use.configure(state='normal')
                self.button_display_stored_results.configure(state='normal')
                self.button_display_raw_output.configure(state='normal')
                self.button_check_plots.configure(state='normal')
            Thread(target=action).start()

class App():

    def __init__(self, root):
        self.root = root
        root.title('LEAF-chia-plot-check-organiser | ' + open('version.txt' if path.isfile('version.txt') else path.join(sys._MEIPASS, 'version.txt') , 'r').read())

        controls_frame = ttk.Labelframe(text="Controls")
        controls_frame.grid(row=0, column=0, sticky="nsw")
        self.controls_frame = FormControls(controls_frame)

        console_frame = ttk.Labelframe(text="Console")
        console_frame.grid(row=1, column=0, sticky="nsew", columnspan=2)
        self.console_frame = ConsoleUi(console_frame)

        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        self.root.bind('<Control-q>', self.quit)
        signal(SIGINT, self.quit)

    def quit(self):
        self.root.destroy()

def main():
    root = tix.Tk()
    app = App(root)
    app.root.mainloop()

if __name__ == '__main__':
    main()