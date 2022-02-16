import tkinter as tk
from time import sleep
from queue import Empty
from os import path
import webbrowser
import sys
from PIL import Image
from signal import signal,\
    SIGINT
from threading import Thread
from logging import getLogger
from tkinter.scrolledtext import Text, Scrollbar, ScrolledText
from tkinter import tix, simpledialog
from tkinter import ttk, N, S, E, W, END, Label, NONE

from _00_base import configure_logger_and_queue
from _00_back_end import LEAF_back_end,\
    configuration

class buttons_label_state_change():
    combobox_coin_to_use: ttk.Combobox
    button_display_stored_results: ttk.Button
    button_display_raw_output: ttk.Button
    button_check_plots: ttk.Button
    label_backend_status: ttk.Label
    _log: getLogger

    def __init__(self):

        super(buttons_label_state_change, self).__init__()

    def get_buttons_reference(self):

        self.buttons = [self.combobox_coin_to_use,
                        self.button_display_stored_results,
                        self.button_display_raw_output,
                        self.button_check_plots
                        ]
    def disable_all_buttons(self):
        self.get_buttons_reference()
        [button.configure(state='disabled') for button in self.buttons]
        self._log.info('Controls are now disabled until the operation is done. Please wait ...')

    def enable_all_buttons(self):
        self.get_buttons_reference()
        [button.configure(state='enabled') for button in self.buttons]
        self._log.info('Controls are now enabled')

    def backend_label_free(self):
        self.label_backend_status.configure(text="Doing nothing ...",
                                            fg='#33cc33')

    def backend_label_busy(self,
                           text: str):
        self.label_backend_status.configure(text=text,
                                            fg='#ff3300')

class sponsor_reminder():
    def __init__(self, frame):
        self.frame = frame

        self.label_sponsor_logo = Label(self.frame, text='Sponsor')
        self.label_sponsor_logo.grid(column=0, row=0)
        donation_img = 'donation.gif' if path.isfile('donation.gif') else path.join(sys._MEIPASS, 'donation.gif')
        info = Image.open(donation_img)
        self.frameCnt = info.n_frames-3
        self.sleep_between_frames = 0.1
        self.frames = [tk.PhotoImage(file=donation_img, format='gif -index %i' % (i)) for i in range(self.frameCnt)]

        self.label_sponsor_text = Label(self.frame,
                                        text='Found this tool helpful?'
                                             '\n\nWant to contribute to its development ?'
                                             '\n\nYou can make a donation to the author.'
                                             '\n\nClick this text for more info. Thank you :)',
                                        font=10)
        self.label_sponsor_text.grid(column=1, row=0)
        self.label_sponsor_text.bind("<Button-1>", self.sponsor_link)

        Thread(target=self.sponsor_gif_animation).start()

    def sponsor_link(self,
                     *args):
        webbrowser.open_new('https://github.com/ageorge95/LEAF-chia-plot-check-organiser#support')

    def sponsor_gif_animation(self):
        while True:
            for frame_index in range(self.frameCnt):
                frame = self.frames[frame_index]
                self.label_sponsor_logo.configure(image=frame)
                sleep(self.sleep_between_frames)
            sleep(self.sleep_between_frames)

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

        self.scrolled_text = Text(frame, state='disabled', width=100, height=25, wrap=NONE, xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
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

class FormControls(buttons_label_state_change,
                   LEAF_back_end,
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

        self.label_backend_status_notify = Label(self.frame, text='Back-end status:')
        self.label_backend_status_notify.grid(column=2, row=1)
        self.label_backend_status = Label(self.frame, text="Doing nothing ...", fg='#33cc33')
        self.label_backend_status.grid(column=2, row=2)

        self.separator_filtering_v = ttk.Separator(self.frame, orient='vertical')
        self.separator_filtering_v.grid(column=1, row=0, rowspan=10, sticky=(N, S))

        self.separator_filtering_h = ttk.Separator(self.frame, orient='horizontal')
        self.separator_filtering_h.grid(column=0, row=3, columnspan=2, sticky=(W, E))

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
            def action():
                self.disable_all_buttons()
                self.backend_label_busy(text='Busy with displaying stored results !')
                self.print_stored_results(coin=self.coin_to_use.get())
                self.enable_all_buttons()
                self.backend_label_free()
            Thread(target=action).start()

    def master_display_raw_output(self):
        if self.check_coin_selection() and self.precheck_duplicates(self.coin_to_use.get()):
            def plot_name(): # MUST be in the same thread, otherwise the new window trick must be done
                newWin = tix.Tk()
                newWin.withdraw()
                to_return = simpledialog.askstring(title="Input Required",
                                                   prompt="Please input the name of the plot for which you want to display the raw output:",
                                                   parent=newWin)
                newWin.destroy()
                return to_return

            def action():
                self.disable_all_buttons()
                self.backend_label_busy(text='Busy with displaying raw output !')
                self.print_raw_output(coin=self.coin_to_use.get(),
                                      filter_string=plot_name())
                self.enable_all_buttons()
                self.backend_label_free()

            Thread(target=action).start()

    def master_check_plots(self):
        if self.check_coin_selection() and self.precheck_duplicates(self.coin_to_use.get()):
            def action():
                self.backend_label_busy(text='Busy with checking plots !')
                self._log.info('Checking the plots.')
                self.disable_all_buttons()
                self.check_plots(coin=self.coin_to_use.get())
                self._log.info('Plots check completed. Hit that "Display plots check" button to see the results.')
                self.enable_all_buttons()
                self.backend_label_free()
            Thread(target=action).start()

class FormInput():

    def __init__(self, frame):
        self.frame = frame

        self.scrolled_text_input = ScrolledText(self.frame, width=58, height=28)
        self.scrolled_text_input.grid(row=0, column=0, sticky=(N, S, W, E))
        self.scrolled_text_input.configure(font='TkFixedFont')
        self.tip_text_input = tix.Balloon(self.frame)
        self.tip_text_input.bind_widget(self.scrolled_text_input, balloonmsg="Insert here the mnemonic (1 mnemonic 1 line) or the wallet addresses (x addresses 1 line).")

    def return_input(self):
        return self.scrolled_text_input.get("1.0", END).split('\n')

class App():

    def __init__(self, root):
        self.root = root
        self.root.title('LEAF-chia-plot-check-organiser | ' + open('version.txt' if path.isfile('version.txt') else path.join(sys._MEIPASS, 'version.txt') , 'r').read())
        self.root.iconbitmap('icon.ico' if path.isfile('icon.ico') else path.join(sys._MEIPASS, 'icon.ico'))

        sponsor_frame = ttk.Labelframe(text="Sponsor")
        sponsor_frame.grid(row=0, column=1, sticky="w")
        self.sponsor_frame = sponsor_reminder(sponsor_frame)

        controls_frame = ttk.Labelframe(text="Controls")
        controls_frame.grid(row=0, column=0, sticky="nsw")
        self.controls_frame = FormControls(controls_frame)

        console_frame = ttk.Labelframe(text="Console")
        console_frame.grid(row=1, column=0, sticky="nsew")
        self.console_frame = ConsoleUi(console_frame)

        input_frame = ttk.Labelframe(text="Input")
        input_frame.grid(row=1, column=1, sticky="nsew")
        self.input_frame = FormInput(input_frame)

        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        self.root.bind('<Control-q>', self.quit)
        signal(SIGINT, self.quit)

    def quit(self,
             *args):
        # self.root.destroy()
        sys.exit()

def main():
    root = tix.Tk()
    root.resizable(False, False)
    app = App(root)
    app.root.mainloop()

if __name__ == '__main__':
    main()