import tkinter as tk
from tkinter import filedialog, simpledialog, Menu  # Добавляем Menu в импорт
import csv
import configparser
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class TaskDialog(simpledialog.Dialog):
    def __init__(self, parent, task=None, comments=None, end_date=None):
        self.result = None
        self.comment_text = None
        self.title_entry = None
        self.title_var = None
        self.end_date_var = None
        self.task = task
        self.comments = comments or []
        self.end_date = end_date or datetime.now().strftime("%d.%m.%y")
        super().__init__(parent, title="Добавление / Редактирование задачи")

    def body(self, master):
        tk.Label(master, text="Тема:").grid(row=0)
        self.title_var = tk.StringVar(master, value=self.task or "")
        self.title_entry = tk.Entry(master, textvariable=self.title_var)
        self.title_entry.grid(row=0, column=1)
        if self.task:
            self.title_entry.configure(state='disabled')

        tk.Label(master, text="Комментарий:").grid(row=1)
        self.comment_text = tk.Text(master, height=4, width=50, wrap='word')
        self.comment_text.grid(row=1, column=1)
        if self.comments:
            self.comment_text.insert(tk.END, "\n\n".join(self.comments))

        tk.Label(master, text="Дата окончания:").grid(row=2)
        self.end_date_var = tk.StringVar(master, value=self.end_date)
        self.end_date_entry = tk.Entry(master, textvariable=self.end_date_var)
        self.end_date_entry.grid(row=2, column=1)

        return self.title_entry

    def apply(self):
        title = self.title_var.get()
        comment = self.comment_text.get("1.0", 'end-1c').strip()
        end_date = self.end_date_var.get()
        self.result = title, comment, end_date
        logging.debug(f'Применяем изменения: Заголовок - {title}, Комментарий - {comment}, Дата окончания - {end_date}')


class KanbanApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.task_entry = None
        self.title("Kanban Board")
        self.tasks = {}
        self.columns = ['Сделать', 'В процессе', 'Сделано']
        self.column_listboxes = {col: tk.Listbox(self) for col in self.columns}
        self.active_listbox = None  # Ссылка на активный Listbox
        self.setup_ui()
        self.load_from_ini("tasks.ini")
        self.create_context_menu()  # Убедитесь, что метод вызывается в __init__

    def setup_ui(self):
        self.task_entry = tk.Entry(self)
        self.task_entry.grid(row=0, column=0, columnspan=len(self.columns), sticky='ew')
        self.task_entry.bind('<Return>', self.create_task_from_entry)
        self.grid_rowconfigure(2, weight=1)
        for i in range(3):
            self.grid_columnconfigure(i, weight=1)
        for i, column_name in enumerate(self.columns):
            tk.Label(self, text=column_name, font=('Helvetica', 16), relief='ridge', width=15).grid(row=1, column=i,
                                                                                                    sticky='ew')
        for i, (col, lb) in enumerate(self.column_listboxes.items()):
            lb.bind('<Double-Button-1>', self.show_comments)
            lb.bind('<KeyPress>', self.move_task)
            lb.bind('<Button-3>', self.show_context_menu)  # Правая кнопка мыши для вызова контекстного меню
            lb.grid(row=2, column=i, padx=5, pady=5, sticky='nswe')
        self.add_task_button = tk.Button(self, text="Добавить задачу", command=self.open_task_dialog)
        self.add_task_button.grid(row=3, column=0, columnspan=2, sticky='ew')
        self.load_tasks_button = tk.Button(self, text="Загрузить задачи из CSV", command=self.load_tasks_from_csv)
        self.load_tasks_button.grid(row=3, column=2, sticky='ew')
        self.create_context_menu()
        # Создаем Listbox с возможностью множественного выбора
        self.column_listboxes[column_name] = tk.Listbox(self, selectmode=tk.EXTENDED)
        self.column_listboxes[column_name].grid(row=2, column=i, padx=5, pady=5, sticky='nswe')
        # Привязка события правой кнопки мыши к методу показа контекстного меню
        self.column_listboxes[column_name].bind('<Button-2>', self.show_context_menu)  # Используем <Button-2> для macOS
        # Привязки для других действий без изменений
    def create_context_menu(self):
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Удалить задачу(и)", command=self.delete_selected_tasks)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def delete_selected_tasks(self):
        for col, lb in self.column_listboxes.items():
            selected_indices = list(lb.curselection())
            selected_indices.reverse()  # Переворачиваем список, чтобы удалять с конца
            for i in selected_indices:
                task_title = lb.get(i).split('\n')[0]
                if task_title in self.tasks:
                    del self.tasks[task_title]
                lb.delete(i)
        self.save_to_ini("tasks.ini")

    def load_tasks_from_csv(self):
        filename = filedialog.askopenfilename(title="Открыть CSV файл", filetypes=(("CSV файлы", "*.csv"), ("Все файлы", "*.*")))

        if not filename:
            return
        with open(filename, newline='', encoding='utf-8') as csvfile:
            task_reader = csv.reader(csvfile)
            for row in task_reader:
                print(row)  # Вывод каждой строки для диагностики
                if row:
                    title = row[0]
                    comments = [row[1]] if len(row) > 1 else []
                    status = row[2] if len(row) > 2 else 'Сделать'
                    end_date = row[3] if len(row) > 3 else None
                    self.add_task(title, comments, status, end_date)

    def create_task_from_entry(self, event=None):
        title = self.task_entry.get()
        if title:
            self.add_task(title, [], 'Сделать', datetime.now().strftime("%d.%m.%y"))
            self.task_entry.delete(0, tk.END)

    def update_task_list(self):
        # Пример реализации метода
        for col, lb in self.column_listboxes.items():
            lb.delete(0, tk.END)  # Очищаем текущие элементы
            for title, details in self.tasks.items():
                if details['status'] == col:
                    display_text = f" {title}\n [Завершить: {details['end_date']}]"
                    lb.insert(tk.END, display_text)

    def open_task_dialog(self):
        dialog = TaskDialog(self)
        if dialog.result:
            title, comment, end_date = dialog.result
            # Вызов add_task с явным указанием status и end_date
            self.add_task(title, [comment], 'Сделать', end_date)

    def add_task(self, title, comments, status='Сделать', end_date=None):
        # Преобразуем comments в строку перед сохранением
        comments_str = ','.join(comments)  # Преобразование списка комментариев в строку
        # Проверка валидности статуса
        if status not in self.columns:
            print(f"Ошибка: статус '{status}' не существует.")
            return  # Прекращаем выполнение функции, если статус невалиден

        # Инициализация переменной для текста отображения задачи
        display_text = title

        # Проверка и коррекция даты
        if end_date and end_date != "Не указано":
            try:
                # Попытка преобразовать строку даты в объект datetime
                date_obj = datetime.strptime(end_date, "%d.%m.%y")
                # Рассчитываем разницу в днях, добавляя 1, чтобы включить и конечный день
                days_left = (date_obj - datetime.now()).days + 1
                display_text += f"\n{end_date} ({days_left} дней)"
            except ValueError:
                # Если преобразование не удалось, выводим сообщение об ошибке
                print(f"Ошибка: дата '{end_date}' не соответствует формату 'дд.мм.гг'.")
                return  # Прекращаем выполнение функции, если дата невалидна

        elif not end_date or end_date == "Не указано":
            # Если дата не указана или равна "Не указано", не добавляем информацию о дате к задаче
            display_text += "\n [Дата окончания не указана]"

        # Добавление задачи в соответствующий Listbox
        if status in self.column_listboxes:
            self.column_listboxes[status].insert(tk.END, display_text)
            self.tasks[title] = {'comments': comments, 'status': status, 'end_date': end_date}
            self.save_to_ini("tasks.ini")

    def edit_task(self, old_title, new_title, new_comments, new_status, new_end_date):
        # Проверяем, существует ли задача с таким названием
        if old_title in self.tasks:
            # Удаляем старую запись задачи
            del self.tasks[old_title]
            # Создаем новую запись задачи с обновленными данными
            self.tasks[new_title] = {
                'comments': new_comments,
                'status': new_status,
                'end_date': new_end_date
            }
            # Сохраняем изменения в файл
            self.save_to_ini("tasks.ini")
            self.update_task_list()  # Обновление списка задач
        else:
            print("Задача для редактирования не найдена.")

    def show_comments(self, event):
        lb = event.widget
        selection = lb.curselection()
        if selection:
            task_info = lb.get(selection[0]).split('\n')[0]
            task = next((title for title in self.tasks if title.startswith(task_info)), None)
            if task:
                comments = self.tasks[task]['comments']
                end_date = self.tasks[task]['end_date']
                dialog = TaskDialog(self, task, comments, end_date)
                if dialog.result:
                    # Этот блок должен обновлять существующую задачу
                    new_title, new_comments, new_end_date = dialog.result
                    self.edit_task(task, new_title, [new_comments], self.tasks[task]['status'], new_end_date)

    def move_task(self, event):
        lb = event.widget
        if event.keysym in ['Left', 'Right'] and lb.curselection():
            selection = lb.curselection()
            display_text = lb.get(selection[0])
            task_info = display_text.split('\n')[0]
            task = next((title for title in self.tasks if title.startswith(task_info)), None)
            if task:
                lb.delete(selection[0])
                current_column = None
                for col_name, listbox in self.column_listboxes.items():
                    if listbox is lb:
                        current_column = col_name
                        break
                if current_column is not None:
                    current_index = self.columns.index(current_column)
                    new_index = (current_index + (1 if event.keysym == 'Right' else -1)) % len(self.columns)
                    new_column = self.columns[new_index]
                    new_lb = self.column_listboxes[new_column]
                    new_lb.insert(tk.END, display_text)
                    self.tasks[task]['status'] = new_column
                    self.save_to_ini("tasks.ini")

    def save_to_ini(self, filename):
        config = configparser.ConfigParser()
        for title, details in self.tasks.items():
            end_date = str(details.get('end_date', 'Не указано'))  # Преобразование в строку
            comments = ','.join([str(comment) for comment in details['comments']])  # Убедимся, что комментарии - строки
            status = str(details['status'])  # Преобразование в строку
            config[title] = {
                'comments': comments,
                'status': status,
                'end_date': end_date
            }
        try:
            with open(filename, 'w') as configfile:
                config.write(configfile)
            print(f"Задачи успешно сохранены в {filename}.")
        except Exception as e:
            print(f"Ошибка при сохранении задач: {e}")

    def load_from_ini(self, filename):
        config = configparser.ConfigParser()
        config.read(filename)
        for title in config.sections():
            comments = config[title]['comments'].split(',') if config[title]['comments'] else []
            status = config[title]['status']
            end_date_str = config[title].get('end_date', 'Не указано')
            if end_date_str in ['None', 'Не указано']:  # Проверка на 'None' или другое значение по умолчанию
                end_date = 'Не указано'
            else:
                end_date = end_date_str
            print(f"Загрузка задачи: {title}, Статус: {status}, Дата окончания: {end_date}")
            self.add_task(title, comments, status, end_date)

    def on_close(self):
        self.save_to_ini("tasks.ini")
        self.destroy()


if __name__ == "__main__":
    app = KanbanApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
