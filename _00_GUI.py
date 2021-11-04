import tkinter as tk
from queue import Empty
from os import path,\
    listdir
from signal import signal,\
    SIGINT
from tkinter.scrolledtext import ScrolledText, Text, Scrollbar
from tkinter import ttk, N, S, E, W, END, Label, BOTTOM, RIGHT, NONE

from _00_base import configure_logger_and_queue
from _00_back_end import LEAF_back_end

class ConsoleUi(configure_logger_and_queue):
    """Poll messages from a logging queue and display them in a scrolled text widget"""

    def __init__(self, frame):

        super(ConsoleUi, self).__init__()

        self.frame = frame

        # add a button to clear the text
        self.button_clear_console = ttk.Button(self.frame, text='CLEAR CONSOLE', command=self.clear_console)
        self.button_clear_console.grid(column=0, row=0, sticky=W)

        # Create a ScrolledText wdiget
        self.h_scroll = Scrollbar(self.frame, orient='horizontal')
        self.h_scroll.grid(row=2, column=0, sticky=(W, E))
        self.v_scroll = Scrollbar(self.frame, orient='vertical')
        self.v_scroll.grid(row=1, column=1, sticky=(N, S))

        self.scrolled_text = Text(frame, state='disabled', width=100, height=50, wrap=NONE, xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
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

class FormControls(configure_logger_and_queue,
                   LEAF_back_end):

    def __init__(self,
                 frame,
                 input_frame):
        super(FormControls, self).__init__()

        self.input_frame = input_frame
        self.frame = frame

        self.label_coin_to_use = Label(self.frame, text='Coin to be used:')
        self.coin_to_use = tk.StringVar()
        self.combobox_coin_to_use = ttk.Combobox(
            self.frame,
            textvariable=self.coin_to_use,
            width=45,
            state='readonly',
            values=self.return_configured_coins()
        )
        self.combobox_coin_to_use.current(0)
        self.label_coin_to_use.grid(column=0, row=1, sticky=(W))
        self.combobox_coin_to_use.grid(column=0, row=2, sticky=(W))

        self.filter_by_input = True
        self.button_filter_by_input = tk.Button(self.frame, text='Filter by input', command=self.toggle_filter_by_input, relief="raised")
        self.button_filter_by_input.grid(column=0, row=4, sticky=W)

        self.separator_filtering = ttk.Separator(self.frame, orient='horizontal')
        self.separator_filtering.grid(column=0, row=6, sticky=(W, E), pady=10)

        self.button_display_stored_results = ttk.Button(self.frame, text='Display stored data', command=self.master_display_stored_results)
        self.button_display_stored_results.grid(column=0, row=8, sticky=W)

        self.button_check_plots = ttk.Button(self.frame, text='Check plots', command=self.master_check_plots)
        self.button_check_plots.grid(column=0, row=10, sticky=W)

    def toggle_filter_by_input(self):

        if self.button_filter_by_input.config('relief')[-1] == 'sunken':
            self.button_filter_by_input.config(relief="raised", text='Filter by input')
            self.filter_by_input = True
            self._log.info('Will filter by input.')
        else:
            self.button_filter_by_input.config(relief="sunken", text='Parse all stored data')
            self.filter_by_input = False
            self._log.info('Will parse all stored data.')

    def master_display_stored_results(self):
        self.print_stored_results(coin=self.coin_to_use.get(),
                                  filter_by_input=self.filter_by_input,
                                  list_of_filenames=self.input_frame.return_input_filenames())

    def master_check_plots(self):
        self.combobox_coin_to_use.configure(state='disabled')
        self.button_filter_by_input.configure(state='disabled')
        self.button_display_stored_results.configure(state='disabled')
        self.button_check_plots.configure(state='disabled')
        self._log.info('Checking the plots. Controls are now disabled until the operation is done. Please wait ...')
        self.check_plots(coin=self.coin_to_use.get(),
                         list_of_plots_fiepaths=self.input_frame.return_input_filepaths())
        self._log.info('Plots check completed ! Controls are now enabled.')
        self.combobox_coin_to_use.configure(state='normal')
        self.button_filter_by_input.configure(state='normal')
        self.button_display_stored_results.configure(state='normal')
        self.button_check_plots.configure(state='normal')

class FormInput():

    def __init__(self, frame):
        self.frame = frame

        self.scrolled_text_input_links = ScrolledText(self.frame, width=50, height=45)
        self.scrolled_text_input_links.grid(row=0, column=0, sticky=(N, S, W, E))
        self.scrolled_text_input_links.configure(font='TkFixedFont')

    def return_input_filenames(self):
        all_input = self.scrolled_text_input_links.get("1.0", END).split('\n')
        to_return = []
        for entry in all_input:
            if path.isfile(entry):
                if entry.endswith('.plot'):
                    to_return.append(path.basename(entry))
            if path.isdir(entry):
                for file in listdir(entry):
                    if file.endswith('.plot'):
                        to_return.append(path.basename(file))
            to_return.append(entry)
        return to_return[:-1]

    def return_input_filepaths(self):
        all_input = self.scrolled_text_input_links.get("1.0", END).split('\n')
        to_return = []
        for entry in all_input:
            if path.isfile(entry):
                if entry.endswith('.plot'):
                    to_return.append(entry)
            if path.isdir(entry):
                for file in listdir(entry):
                    if file.endswith('.plot'):
                        to_return.append(path.join(entry, file))
            to_return.append(entry)
        return to_return[:-1]

class App():

    def __init__(self, root):
        self.root = root
        root.title('LEAF-chia-plot-check-organiser')

        input_frame = ttk.Labelframe(text="Input")
        input_frame.grid(row=1, column=0, sticky="nsew")
        self.input_frame = FormInput(input_frame)

        controls_frame = ttk.Labelframe(text="Controls")
        controls_frame.grid(row=0, column=0, sticky="nsew")
        self.controls_frame = FormControls(controls_frame,
                                           self.input_frame)

        console_frame = ttk.Labelframe(text="Console")
        console_frame.grid(row=0, column=1, sticky="nsew", rowspan=2)
        self.console_frame = ConsoleUi(console_frame)

        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        self.root.bind('<Control-q>', self.quit)
        signal(SIGINT, self.quit)

    def quit(self):
        self.root.destroy()

def main():
    root = tk.Tk()
    app = App(root)
    app.root.mainloop()

if __name__ == '__main__':
    main()