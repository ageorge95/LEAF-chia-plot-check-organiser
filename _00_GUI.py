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
from tkinter import tix, simpledialog, Entry
from tkinter import ttk, N, S, E, W, END, Label, NONE
from yaml import safe_load
from traceback import format_exc

from _00_base import configure_logger_and_queue
from _00_back_end import LEAF_back_end

class buttons_label_state_change():
    button_display_stored_results_by_proof_ratio: ttk.Button
    button_display_stored_results_by_tsted_challen: ttk.Button
    button_display_histograms: ttk.Button
    button_check_plots: ttk.Button
    label_backend_status: ttk.Label
    _log: getLogger

    def __init__(self):

        super(buttons_label_state_change, self).__init__()

    def get_buttons_reference(self):

        self.buttons = [self.button_display_stored_results_by_proof_ratio,
                        self.button_display_stored_results_by_tsted_challen,
                        self.button_display_histograms,
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

        self.scrolled_text = Text(frame, state='disabled', width=100, height=29, wrap=NONE, xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
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
                 frame,
                 input_frame,
                 progress_frame):
        super(FormControls, self).__init__()

        self.stop_flag = False

        self._log = getLogger()

        self.frame = frame
        self.input_frame = input_frame
        self.progress_frame = progress_frame

        self.label_challenges_to_check = Label(self.frame, text='Nr of Challenges to check')
        self.entry_challenges_to_check = Entry(self.frame)
        self.entry_challenges_to_check.insert(END, '100')
        self.label_challenges_to_check.grid(column=0, row=1)
        self.entry_challenges_to_check.grid(column=0, row=2)

        self.label_delay_between_check = Label(self.frame, text='Delay[s] between challenge check')
        self.entry_delay_between_check = Entry(self.frame)
        self.entry_delay_between_check.insert(END, '0')
        self.label_delay_between_check.grid(column=0, row=3)
        self.entry_delay_between_check.grid(column=0, row=4)

        self.label_backend_status_notify = Label(self.frame, text='Back-end status:')
        self.label_backend_status_notify.grid(column=4, row=1)
        self.label_backend_status = Label(self.frame, text="Doing nothing ...", fg='#33cc33')
        self.label_backend_status.grid(column=4, row=2)

        self.separator_filtering_v = ttk.Separator(self.frame, orient='vertical')
        self.separator_filtering_v.grid(column=3, row=0, rowspan=15, sticky=(N, S))

        self.separator_filtering_h = ttk.Separator(self.frame, orient='horizontal')
        self.separator_filtering_h.grid(column=0, row=5, columnspan=3, sticky=(W, E), pady=(10,10))

        self.label_hover_hints = Label(self.frame, text='NOTE: Hover on the elements below for more info.')
        self.label_hover_hints.grid(column=0, row=6, columnspan=2)

        self.button_display_stored_results_by_proof_ratio = ttk.Button(self.frame, text='Display plot checks__by proofs ratio', command=lambda :self.master_display_stored_results('proofs_found'))
        self.button_display_stored_results_by_proof_ratio.grid(column=0, row=7, sticky=W)
        self.tip_display_stored_results = tix.Balloon(self.frame)
        self.tip_display_stored_results.bind_widget(self.button_display_stored_results_by_proof_ratio, balloonmsg="Will display the plot check results for all the plots that are in the specified paths;"
                                                                                                  " Ordered by the proofs ratio.")

        self.button_display_stored_results_by_tsted_challen = ttk.Button(self.frame, text='Display plot checks__by tested challenges', command=lambda :self.master_display_stored_results('challenges_tried'))
        self.button_display_stored_results_by_tsted_challen.grid(column=0, row=8, sticky=W)
        self.tip_display_stored_results = tix.Balloon(self.frame)
        self.tip_display_stored_results.bind_widget(self.button_display_stored_results_by_tsted_challen, balloonmsg="Will display the plot check results for all the plots that are in the specified paths;"
                                                                                                  " Ordered by the nr of tested challenges.")

        self.button_display_histograms = ttk.Button(self.frame, text='Display histograms', command=self.master_display_histograms)
        self.button_display_histograms.grid(column=0, row=9, sticky=W)
        self.tip_display_stored_results = tix.Balloon(self.frame)
        self.tip_display_stored_results.bind_widget(self.button_display_histograms, balloonmsg="Will display various histograms based on the plots found in the specified directories.")

        self.button_check_plots = ttk.Button(self.frame, text='Check plots', command=self.master_check_plots)
        self.button_check_plots.grid(column=0, row=11, sticky=W, columnspan=2)
        self.tip_check_plots = tix.Balloon(self.frame)
        self.tip_check_plots.bind_widget(self.button_check_plots,balloonmsg="Will begin the plots check using the coin selected above.")

        self.button_stop_plots = ttk.Button(self.frame, text='STOP check', command=self.set_stop_flag)
        self.button_stop_plots.grid(column=1, row=11, sticky=E, columnspan=2)
        self.tip_stop_plots = tix.Balloon(self.frame)
        self.tip_stop_plots.bind_widget(self.button_check_plots,balloonmsg="Will stop the current check. Progress is saved. On the next execution the check will resume.")

    def input_sanity_check(self):
        success = True
        message = ''

        try:
            int(self.entry_challenges_to_check.get())
        except:
            success = False
            message += f"{ self.entry_challenges_to_check.get() } is not really a number is it ? Correct that and try again !"

        try:
            float(self.entry_delay_between_check.get())
        except:
            success = False
            message += f"{ self.entry_delay_between_check.get() } is not really a number is it ? Correct that and try again !"

        return {'success': success,
                'message': message}

    def master_display_histograms(self):
        def action():
            self.disable_all_buttons()
            self.backend_label_busy(text='Busy with computing the histograms !')
            self.parse_input_and_get_paths(self.input_frame.return_input())
            self.trigger_histogram_build()
            self.enable_all_buttons()
            self.backend_label_free()
        Thread(target=action).start()

    def master_display_stored_results(self,
                                      filter_by):
        def action():
            self.disable_all_buttons()
            self.backend_label_busy(text='Busy with displaying stored results !')
            self.parse_input_and_get_paths(self.input_frame.return_input())
            self.print_stored_results(filter_by)
            self.enable_all_buttons()
            self.backend_label_free()
        Thread(target=action).start()

    def master_check_plots(self):
        def action():
            self.backend_label_busy(text='Busy with checking plots !')
            self._log.info('Checking the plots.')
            self.disable_all_buttons()
            self.parse_input_and_get_paths(self.input_frame.return_input())
            self.check_plots(nr_challenges=int(self.entry_challenges_to_check.get()),
                             delay_between_checks=float(self.entry_delay_between_check.get()),
                             progress_callback=self.progress_frame.update_progress_callback,
                             stop_flag_check=self.stop_flag_check)
            self._log.info('Plots check completed. Hit that "Display plots check" button to see the results.')
            self.enable_all_buttons()
            self.stop_flag = False
            self.backend_label_free()

        sanity_check = self.input_sanity_check()
        if sanity_check['success']:
            Thread(target=action).start()
        else:
            self._log.error(f"'Sanity check Failed:\n{ sanity_check['message'] }'")

    def set_stop_flag(self):
        self.stop_flag = True

    def stop_flag_check(self):
        return self.stop_flag

class FormInput():

    def __init__(self, frame):
        self.frame = frame

        self._log = getLogger()

        self.button_import_paths = ttk.Button(self.frame, text='Import paths', command=self.import_paths)
        self.button_import_paths.grid(column=0, row=0, sticky=W)

        self.import_paths = [path.join(path.expanduser("~"),'.chia', 'mainnet', 'config', 'config.yaml'),
                        path.join(path.expanduser("~"),'.chives', 'mainnet', 'config', 'config.yaml')]
        self.label_import_paths = Label(self.frame, text=';\n'.join(self.import_paths))
        self.label_import_paths.grid(column=0, row=1, rowspan=2)

        self.scrolled_text_input = ScrolledText(self.frame, width=58, height=28)
        self.scrolled_text_input.grid(row=3, column=0, sticky=(N, S, W, E))
        self.scrolled_text_input.configure(font='TkFixedFont')
        self.tip_text_input = tix.Balloon(self.frame)
        self.tip_text_input.bind_widget(self.scrolled_text_input, balloonmsg="Insert plot filepaths or folder paths containg plots (1 entry per line).")

    def import_paths(self):
        all_plot_paths = []
        for import_path in self.import_paths:
            try:
                self._log.info(f'Importing paths from { import_path } ...')
                self.button_import_paths.configure(state='disabled')
                with open(import_path, 'r') as input_yaml_config:
                    yaml_config = safe_load(input_yaml_config)
                plots_paths = yaml_config['harvester']['plot_directories']
                all_plot_paths += plots_paths
                self._log.info('Paths imported successfully !')
            except:
                self._log.error(f'Failed to import the paths from { import_path }\n{ format_exc(chain=False) }')

        self.scrolled_text_input.delete('1.0', tk.END)
        self.scrolled_text_input.insert(tk.INSERT, '\n'.join(all_plot_paths))

        self.button_import_paths.configure(state='normal')

    def return_input(self):
        return self.scrolled_text_input.get("1.0", END).strip().split('\n')

class ProgressBar():

    def __init__(self, frame):
        self.frame = frame

        self._log = getLogger()

        self.label_subprogress = Label(self.frame, text='Current task progress: 0 / 0')
        self.label_subprogress.grid(column=0, row=0)
        self.subprogress = ttk.Progressbar(self.frame, orient = "horizontal", length = 1310, mode = "determinate", style = "colour.Horizontal.TProgressbar")
        self.subprogress.grid(column=0, row=1)

        self.label_progress = Label(self.frame, text='Overall progress: 0 / 0')
        self.label_progress.grid(column=0, row=2)
        self.progress = ttk.Progressbar(self.frame, orient = "horizontal", length = 1310, mode = "determinate", style = "colour.Horizontal.TProgressbar")
        self.progress.grid(column=0, row=3)

    def update_progress_callback(self,
                                **kwargs):
        if kwargs.get('subprogress'):
            self.subprogress['maximum'] = kwargs.get('subprogress')['maximum']
            self.subprogress['value'] = kwargs.get('subprogress')['value']
            self.label_subprogress.configure(text=f"Current task progress: { kwargs.get('subprogress')['text'] }")

        if kwargs.get('progress'):
            self.progress['maximum'] = kwargs.get('progress')['maximum']
            self.progress['value'] = kwargs.get('progress')['value']
            self.label_progress.configure(text=f"Overall progress: { kwargs.get('progress')['text'] }" )

class App():

    def __init__(self, root):
        self.root = root
        self.root.title('LEAF-chia-plot-check-organiser | ' + open('version.txt' if path.isfile('version.txt') else path.join(sys._MEIPASS, 'version.txt') , 'r').read())
        self.root.iconbitmap('icon.ico' if path.isfile('icon.ico') else path.join(sys._MEIPASS, 'icon.ico'))

        sponsor_frame = ttk.Labelframe(text="Sponsor")
        sponsor_frame.grid(row=0, column=1, sticky="w")
        self.sponsor_frame = sponsor_reminder(sponsor_frame)

        progress_frame = ttk.Labelframe(text="Progress")
        progress_frame.grid(row=1, column=0, columnspan = 3, sticky='nsew')
        self.progress_frame = ProgressBar(progress_frame)

        input_frame = ttk.Labelframe(text="Input")
        input_frame.grid(row=2, column=1, sticky="nsew")
        self.input_frame = FormInput(input_frame)

        controls_frame = ttk.Labelframe(text="Controls")
        controls_frame.grid(row=0, column=0, sticky="nsw")
        self.controls_frame = FormControls(controls_frame,
                                           self.input_frame,
                                           self.progress_frame)

        console_frame = ttk.Labelframe(text="Console")
        console_frame.grid(row=2, column=0, sticky="nsew")
        self.console_frame = ConsoleUi(console_frame)

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