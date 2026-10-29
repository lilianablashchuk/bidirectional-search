import sys
import os
import random
import time
import csv
from collections import deque
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QSlider,
    QRadioButton, QButtonGroup, QScrollArea, QFrame, QDialog,
    QTextEdit, QLineEdit, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont


class PastelMazeCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = 15
        self.cols = 15
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.start = (0, 0)
        self.goal = (14, 14)

        self.visited_a = {}
        self.visited_b = {}
        self.front_a = set()
        self.front_b = set()
        self.meet_node = None
        self.final_path = []

        self.edit_mode = "wall"
        self.setMinimumSize(420, 420)
        self.on_coords_changed_callback = None

    def set_grid_dimensions(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.start = (0, 0)
        self.goal = (self.rows - 1, self.cols - 1)
        self.reset_search_visuals()
        if self.on_coords_changed_callback:
            self.on_coords_changed_callback(self.start, self.goal)
        self.update()

    def reset_search_visuals(self):
        self.visited_a.clear()
        self.visited_b.clear()
        self.front_a.clear()
        self.front_b.clear()
        self.meet_node = None
        self.final_path = []
        self.update()

    def get_cell_size(self):
        w = self.width() - 20
        h = self.height() - 20
        if self.cols <= 0 or self.rows <= 0:
            return 20, 10, 10
        cell_size = min(w / self.cols, h / self.rows)
        offset_x = (self.width() - cell_size * self.cols) / 2
        offset_y = (self.height() - cell_size * self.rows) / 2
        return cell_size, offset_x, offset_y

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        cell_size, offset_x, offset_y = self.get_cell_size()
        path_set = set(self.final_path)

        for r in range(self.rows):
            for c in range(self.cols):
                rx = offset_x + c * cell_size
                ry = offset_y + r * cell_size
                rect = QRectF(rx, ry, cell_size, cell_size)

                node = (r, c)
                is_wall = (self.grid[r][c] == -1)

                if node == self.start:
                    bg_color = QColor("#48C9B0")  # М'ятний
                elif node == self.goal:
                    bg_color = QColor("#EC7063")  # Кораловий
                elif node == self.meet_node:
                    bg_color = QColor("#F39C12")  # Зустріч хвиль
                elif node in path_set:
                    bg_color = QColor("#52BE80")  # Шлях
                elif is_wall:
                    bg_color = QColor("#2E2A36")  # Стіна
                elif node in self.front_a:
                    bg_color = QColor("#F9E79F")  # Фронт А
                elif node in self.front_b:
                    bg_color = QColor("#FADBD8")  # Фронт В
                elif node in self.visited_a and node in self.visited_b:
                    bg_color = QColor("#BB8FCE")  # Зона зустрічі
                elif node in self.visited_a:
                    bg_color = QColor("#AED6F1")  # Хвиля А
                elif node in self.visited_b:
                    bg_color = QColor("#D7BDE2")  # Хвиля В
                else:
                    bg_color = QColor("#FFFFFF")

                painter.fillRect(rect, QBrush(bg_color))
                painter.setPen(QPen(QColor("#D5DBDB"), 1))
                painter.drawRect(rect)

                if node == self.start or node == self.goal or node == self.meet_node:
                    painter.setPen(QPen(Qt.white))
                    font = QFont("Segoe UI", int(max(7, cell_size * 0.42)), QFont.Bold)
                    painter.setFont(font)
                    txt = "S" if node == self.start else ("G" if node == self.goal else "M")
                    painter.drawText(rect, Qt.AlignCenter, txt)
                elif not is_wall and cell_size >= 13:
                    step_val = None
                    if node in self.visited_a:
                        step_val = self.visited_a[node]
                    elif node in self.visited_b:
                        step_val = self.visited_b[node]

                    if step_val is not None:
                        painter.setPen(QPen(QColor("#34495E")))
                        font = QFont("Segoe UI", int(max(6, cell_size * 0.32)))
                        painter.setFont(font)
                        painter.drawText(rect, Qt.AlignCenter, str(step_val))

    def mousePressEvent(self, event):
        cell_size, offset_x, offset_y = self.get_cell_size()
        col = int((event.x() - offset_x) // cell_size)
        row = int((event.y() - offset_y) // cell_size)

        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.reset_search_visuals()
            if self.edit_mode == "wall":
                if (row, col) != self.start and (row, col) != self.goal:
                    self.grid[row][col] = 0 if self.grid[row][col] == -1 else -1
            elif self.edit_mode == "start":
                if self.grid[row][col] != -1 and (row, col) != self.goal:
                    self.start = (row, col)
                    if self.on_coords_changed_callback:
                        self.on_coords_changed_callback(self.start, self.goal)
            elif self.edit_mode == "goal":
                if self.grid[row][col] != -1 and (row, col) != self.start:
                    self.goal = (row, col)
                    if self.on_coords_changed_callback:
                        self.on_coords_changed_callback(self.start, self.goal)
            self.update()


class MatrixViewerDialog(QDialog):

    def __init__(self, matrix_a, matrix_b, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Матриці хвильових потенціалів")
        self.resize(500, 560)
        self.setStyleSheet("""
            QDialog { background-color: #F8F9FA; font-family: 'Segoe UI'; font-size: 13px; }
            QLabel { color: #2C3E50; font-weight: bold; }
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #D5DBDB;
                border-radius: 6px;
                font-family: 'Consolas';
                font-size: 11px;
                color: #2C3E50;
            }
            QPushButton {
                background-color: #EC407A;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #D81B60; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Розподіл потенціалів хвилі A (від старту S) та хвилі B (від цілі G):"))

        matrix_box = QTextEdit()
        matrix_box.setReadOnly(True)

        matrix_str = "Матриця хвилі A (від старту):\n"
        for row in matrix_a:
            matrix_str += " ".join(f"{val:3}" for val in row) + "\n"
        matrix_str += "\nМатриця хвилі B (від цілі):\n"
        for row in matrix_b:
            matrix_str += " ".join(f"{val:3}" for val in row) + "\n"

        matrix_box.setText(matrix_str)
        layout.addWidget(matrix_box)

        btn_close = QPushButton("Закрити")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


class WaveResultDialog(QDialog):
   
    def __init__(self, metrics, matrix_a, matrix_b, parent=None):
        super().__init__(parent)
        self.matrix_a = matrix_a
        self.matrix_b = matrix_b

        self.setWindowTitle("Двонаправлений хвильовий пошук")
        self.resize(520, 500)
        self.setStyleSheet("""
            QDialog { background-color: #F8F9FA; font-family: 'Segoe UI'; font-size: 13px; }
            QLabel { color: #2C3E50; font-size: 13px; }
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #D5DBDB;
                border-radius: 6px;
                font-family: 'Consolas';
                font-size: 12px;
                color: #2C3E50;
            }
            QPushButton {
                background-color: #EC407A;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 9px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #D81B60; }
            QPushButton.secondary {
                background-color: #FCE4EC;
                color: #880E4F;
                border: 1px solid #F8BBD0;
            }
            QPushButton.secondary:hover { background-color: #F8BBD0; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title_lbl = QLabel("Результати виконання пошуку")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: bold; color: #880E4F;")
        header_layout.addWidget(title_lbl)

        status_text = "Шлях знайдено" if metrics['found'] else "Шлях не знайдено"
        badge_bg = "#48C9B0" if metrics['found'] else "#EC7063"
        status_badge = QLabel(status_text)
        status_badge.setAlignment(Qt.AlignCenter)
        status_badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        status_badge.setContentsMargins(5, 2, 5, 2)
        status_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                color: white;
                font-weight: bold;
                font-size: 11px;
                border-radius: 4px;
                margin: 0px;
                padding: 1px 4px;
            }}
        """)
        header_layout.addWidget(status_badge)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        pct_free = (metrics['free_cells'] / (metrics['rows'] * metrics['cols'])) * 100
        table_html = f"""
        <table style='width: 100%; border-collapse: collapse; line-height: 1.5;'>
            <tr>
                <td style='color: #2C3E50;'>Розмірність сітки:</td>
                <td style='text-align: right;'><b>{metrics['rows']} × {metrics['cols']}</b></td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Частка прохідних клітинок:</td>
                <td style='text-align: right;'>{pct_free:.1f}%</td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Оператор переходу:</td>
                <td style='text-align: right;'><b>{metrics['operator']}</b></td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Початкова вершина (S):</td>
                <td style='text-align: right;'><b>{metrics['start']}</b></td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Цільова вершина (G):</td>
                <td style='text-align: right;'><b>{metrics['goal']}</b></td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Точка зустрічі хвиль:</td>
                <td style='text-align: right;'><b>{metrics['meet_node'] if metrics['meet_node'] else 'немає'}</b></td>
            </tr>
            <tr>
                <td style='height: 8px;'></td>
                <td style='height: 8px;'></td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Довжина шляху (кількість переходів):</td>
                <td style='text-align: right;'><b>{metrics['path_length']}</b></td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Кількість клітинок у шляху:</td>
                <td style='text-align: right;'><b>{metrics['path_cells']}</b></td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Кількість циклів роботи:</td>
                <td style='text-align: right;'><b>{metrics['cycles']}</b></td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Розкрито вершин (A + B):</td>
                <td style='text-align: right;'><b>{metrics['expanded']}</b> ({metrics['expanded_a']} + {metrics['expanded_b']})</td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Відкрито вершин хвилями:</td>
                <td style='text-align: right;'><b>{metrics['marked']}</b> ({metrics['marked_a']} + {metrics['marked_b']})</td>
            </tr>
            <tr>
                <td style='color: #2C3E50;'>Чистий процесорний час:</td>
                <td style='text-align: right;'><b style='color: #D81B60; font-size: 13px;'>{metrics['time_ms']:.4f} мс</b></td>
            </tr>
        </table>
        """
        info_label = QLabel(table_html)
        info_label.setTextFormat(Qt.RichText)
        layout.addWidget(info_label)

        layout.addWidget(QLabel("<b>Координати знайденого маршруту:</b>"))
        path_box = QTextEdit()
        path_box.setReadOnly(True)
        path_box.setFixedHeight(75)
        if metrics['path']:
            coords_str = " → ".join([f"({r},{c})" for r, c in metrics['path']])
            path_box.setText(coords_str)
        else:
            path_box.setText("Маршрут відсутній через топологічний розрив зв'язності.")
        layout.addWidget(path_box)

        btn_matrix = QPushButton("Переглянути матриці хвильових потенціалів")
        btn_matrix.setProperty("class", "secondary")
        btn_matrix.clicked.connect(self.show_matrix_dialog)
        layout.addWidget(btn_matrix)

        btn_close = QPushButton("Зрозуміло")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def show_matrix_dialog(self):
        mat_dlg = MatrixViewerDialog(self.matrix_a, self.matrix_b, self)
        mat_dlg.exec_()


class WavePyQtModernWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Двонаправлений хвильовий алгоритм")
        self.resize(1140, 820)
        self.apply_pastel_theme()

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._step_animation)

        self.queue_a = deque()
        self.queue_b = deque()
        self.dist_a = {}
        self.dist_b = {}
        self.parent_a = {}
        self.parent_b = {}
        self.meet_node = None
        self.cycles_count = 0
        self.expanded_a_count = 0
        self.expanded_b_count = 0
        self.is_running = False

        self.search_elapsed_time = 0.0

        self.setup_ui()
        self.canvas.on_coords_changed_callback = self.on_canvas_coords_changed
        self.on_generate_maze()

    def apply_pastel_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #F8F9FA; font-family: 'Segoe UI'; font-size: 13px; }
            QFrame.card {
                background-color: #FFFFFF;
                border: 1px solid #EAECEE;
                border-radius: 12px;
            }
            QLabel { color: #2C3E50; font-size: 13px; }
            QLabel.sectionTitle {
                color: #880E4F;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 4px;
            }
            QPushButton {
                background-color: #FCE4EC;
                color: #880E4F;
                border: 1px solid #F8BBD0;
                border-radius: 8px;
                padding: 7px 12px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #F8BBD0; }
            QPushButton.primary {
                background-color: #EC407A;
                color: #FFFFFF;
                border: none;
                font-size: 13px;
                font-weight: bold;
                padding: 9px 12px;
            }
            QPushButton.primary:hover { background-color: #D81B60; }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D5DBDB;
                border-radius: 6px;
                padding: 5px;
                color: #2C3E50;
                font-size: 13px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #F8BBD0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #EC407A;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QRadioButton { color: #2C3E50; font-size: 13px; }
        """)

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        scroll_area = QScrollArea()
        scroll_area.setFixedWidth(360)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(4, 4, 4, 4)
        sidebar_layout.setSpacing(12)

        maze_card = QFrame()
        maze_card.setProperty("class", "card")
        maze_l = QVBoxLayout(maze_card)
        title_maze = QLabel("Параметри лабіринту")
        title_maze.setProperty("class", "sectionTitle")
        maze_l.addWidget(title_maze)

        dim_layout = QHBoxLayout()
        dim_layout.addWidget(QLabel("Розмір:"))
        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(5, 35)
        self.spin_rows.setValue(15)
        dim_layout.addWidget(self.spin_rows)
        lbl_mult = QLabel("×")
        lbl_mult.setAlignment(Qt.AlignCenter)
        lbl_mult.setStyleSheet("font-size: 14px; font-weight: bold; color: #7F8C8D; padding: 0 4px;")
        dim_layout.addWidget(lbl_mult)
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(5, 35)
        self.spin_cols.setValue(15)
        dim_layout.addWidget(self.spin_cols)
        maze_l.addLayout(dim_layout)

        obs_h = QHBoxLayout()
        self.lbl_obs = QLabel("Частка перешкод: 20%")
        obs_h.addWidget(self.lbl_obs)
        maze_l.addLayout(obs_h)

        self.slider_obs = QSlider(Qt.Horizontal)
        self.slider_obs.setRange(0, 60)
        self.slider_obs.setValue(20)
        self.slider_obs.valueChanged.connect(lambda v: self.lbl_obs.setText(f"Частка перешкод: {v}%"))
        maze_l.addWidget(self.slider_obs)

        seed_layout = QHBoxLayout()
        seed_layout.addWidget(QLabel("Seed:"))
        self.edit_seed = QLineEdit("100")
        seed_layout.addWidget(self.edit_seed)
        maze_l.addLayout(seed_layout)

        btn_gen = QPushButton("Згенерувати новий лабіринт")
        btn_gen.clicked.connect(self.on_generate_maze)
        maze_l.addWidget(btn_gen)
        sidebar_layout.addWidget(maze_card)

        edit_card = QFrame()
        edit_card.setProperty("class", "card")
        edit_l = QVBoxLayout(edit_card)
        title_edit = QLabel("Режим редагування клітинок")
        title_edit.setProperty("class", "sectionTitle")
        edit_l.addWidget(title_edit)

        self.btn_group_edit = QButtonGroup(self)
        rb_layout = QHBoxLayout()
        self.rb_wall = QRadioButton("Стіна")
        self.rb_wall.setChecked(True)
        self.rb_start = QRadioButton("Старт (S)")
        self.rb_goal = QRadioButton("Ціль (G)")

        self.btn_group_edit.addButton(self.rb_wall)
        self.btn_group_edit.addButton(self.rb_start)
        self.btn_group_edit.addButton(self.rb_goal)

        rb_layout.addWidget(self.rb_wall)
        rb_layout.addWidget(self.rb_start)
        rb_layout.addWidget(self.rb_goal)
        edit_l.addLayout(rb_layout)

        self.rb_wall.toggled.connect(lambda: self.set_edit_mode("wall"))
        self.rb_start.toggled.connect(lambda: self.set_edit_mode("start"))
        self.rb_goal.toggled.connect(lambda: self.set_edit_mode("goal"))
        sidebar_layout.addWidget(edit_card)

        search_card = QFrame()
        search_card.setProperty("class", "card")
        search_l = QVBoxLayout(search_card)
        title_search = QLabel("Керування пошуком")
        title_search.setProperty("class", "sectionTitle")
        search_l.addWidget(title_search)

        search_l.addWidget(QLabel("Оператор переходу:"))
        self.combo_op = QComboBox()
        self.combo_op.addItems([
            "Ортогональний (4 напр.)",
            "Діагональний (4 напр.)",
            "Комбінований (8 напр.)"
        ])
        search_l.addWidget(self.combo_op)

        coords_layout = QHBoxLayout()
        coords_layout.addWidget(QLabel("S:"))
        self.edit_start = QLineEdit("0,0")
        self.edit_start.setPlaceholderText("r,c")
        self.edit_start.editingFinished.connect(self.on_start_coords_edited)
        coords_layout.addWidget(self.edit_start)

        coords_layout.addWidget(QLabel("G:"))
        self.edit_goal = QLineEdit("14,14")
        self.edit_goal.setPlaceholderText("r,c")
        self.edit_goal.editingFinished.connect(self.on_goal_coords_edited)
        coords_layout.addWidget(self.edit_goal)
        search_l.addLayout(coords_layout)

        btn_swap = QPushButton("Дзеркальна заміна (Старт ↔ Ціль)")
        btn_swap.clicked.connect(self.on_swap_start_goal)
        search_l.addWidget(btn_swap)

        self.btn_start = QPushButton("Запустити анімацію хвилі")
        self.btn_start.setProperty("class", "primary")
        self.btn_start.clicked.connect(self.on_start_search)
        search_l.addWidget(self.btn_start)

        ctrl_btns = QHBoxLayout()
        self.btn_step = QPushButton("Крок")
        self.btn_step.clicked.connect(self.on_step_search)
        self.btn_pause = QPushButton("Пауза")
        self.btn_pause.clicked.connect(self.on_pause_search)
        self.btn_reset = QPushButton("Скинути")
        self.btn_reset.clicked.connect(self.on_reset_search)

        ctrl_btns.addWidget(self.btn_step)
        ctrl_btns.addWidget(self.btn_pause)
        ctrl_btns.addWidget(self.btn_reset)
        search_l.addLayout(ctrl_btns)

        self.btn_instant = QPushButton("Миттєвий розрахунок")
        self.btn_instant.clicked.connect(self.on_instant_search)
        search_l.addWidget(self.btn_instant)

        speed_l = QHBoxLayout()
        speed_l.addWidget(QLabel("Затримка (мс):"))
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(5, 300)
        self.slider_speed.setValue(60)
        speed_l.addWidget(self.slider_speed)
        search_l.addLayout(speed_l)

        sidebar_layout.addWidget(search_card)

        mon_card = QFrame()
        mon_card.setProperty("class", "card")
        mon_l = QVBoxLayout(mon_card)
        title_mon = QLabel("Моніторинг")
        title_mon.setProperty("class", "sectionTitle")
        mon_l.addWidget(title_mon)

        self.lbl_mon_cycles = QLabel("Циклів: 0")
        self.lbl_mon_exp = QLabel("Розкрито (A+B): 0 + 0 = 0")
        self.lbl_mon_status = QLabel("Статус: Готовий до запуску")
        self.lbl_mon_status.setStyleSheet("color: #7D3C98; font-weight: bold; font-size: 13px;")

        mon_l.addWidget(self.lbl_mon_cycles)
        mon_l.addWidget(self.lbl_mon_exp)
        mon_l.addWidget(self.lbl_mon_status)
        sidebar_layout.addWidget(mon_card)

        sidebar_layout.addStretch()
        scroll_area.setWidget(sidebar)
        main_layout.addWidget(scroll_area)


        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.canvas = PastelMazeCanvas()
        right_layout.addWidget(self.canvas, 1)

        legend_frame = QFrame()
        legend_frame.setProperty("class", "card")
        legend_l = QHBoxLayout(legend_frame)
        legend_l.setContentsMargins(10, 8, 10, 8)
        legend_l.setSpacing(14)

        def add_legend_item(color_hex, label_text):
            box = QLabel()
            box.setFixedSize(14, 14)
            box.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #BDC3C7; border-radius: 3px;")
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 12px;")
            legend_l.addWidget(box)
            legend_l.addWidget(lbl)

        add_legend_item("#48C9B0", "Старт (S)")
        add_legend_item("#EC7063", "Ціль (G)")
        add_legend_item("#2E2A36", "Стіна (-1)")
        add_legend_item("#AED6F1", "Хвиля A")
        add_legend_item("#D7BDE2", "Хвиля B")
        add_legend_item("#F39C12", "Зустріч")
        add_legend_item("#52BE80", "Шлях")
        legend_l.addStretch()

        right_layout.addWidget(legend_frame)
        main_layout.addWidget(right_panel, 1)

    def set_edit_mode(self, mode):
        self.canvas.edit_mode = mode

    def on_canvas_coords_changed(self, start_pos, goal_pos):
        self.edit_start.setText(f"{start_pos[0]},{start_pos[1]}")
        self.edit_goal.setText(f"{goal_pos[0]},{goal_pos[1]}")

    def parse_coordinate_text(self, text):
        clean = text.replace("(", "").replace(")", "").replace(";", ",").strip()
        parts = clean.split(",") if "," in clean else clean.split()
        if len(parts) == 2:
            try:
                r = int(parts[0].strip())
                c = int(parts[1].strip())
                return r, c
            except ValueError:
                return None
        return None

    def on_start_coords_edited(self):
        parsed = self.parse_coordinate_text(self.edit_start.text())
        if parsed is not None:
            r, c = parsed
            if 0 <= r < self.canvas.rows and 0 <= c < self.canvas.cols:
                if self.canvas.grid[r][c] != -1 and (r, c) != self.canvas.goal:
                    self.canvas.start = (r, c)
                    self.on_reset_search()
                    self.lbl_mon_status.setText(f"Новий старт: ({r}, {c})")
                    return
    
        self.edit_start.setText(f"{self.canvas.start[0]},{self.canvas.start[1]}")

    def on_goal_coords_edited(self):
        parsed = self.parse_coordinate_text(self.edit_goal.text())
        if parsed is not None:
            r, c = parsed
            if 0 <= r < self.canvas.rows and 0 <= c < self.canvas.cols:
                if self.canvas.grid[r][c] != -1 and (r, c) != self.canvas.start:
                    self.canvas.goal = (r, c)
                    self.on_reset_search()
                    self.lbl_mon_status.setText(f"Нова ціль: ({r}, {c})")
                    return

        self.edit_goal.setText(f"{self.canvas.goal[0]},{self.canvas.goal[1]}")

    def on_generate_maze(self):
        self.on_reset_search()
        rows = self.spin_rows.value()
        cols = self.spin_cols.value()
        obs_percent = self.slider_obs.value() / 100.0

        seed_text = self.edit_seed.text().strip()
        if seed_text:
            try:
                random.seed(int(seed_text))
            except ValueError:
                random.seed(seed_text)
        else:
            random.seed()

        self.canvas.set_grid_dimensions(rows, cols)

        for r in range(rows):
            for c in range(cols):
                if (r, c) == self.canvas.start or (r, c) == self.canvas.goal:
                    self.canvas.grid[r][c] = 0
                else:
                    self.canvas.grid[r][c] = -1 if random.random() < obs_percent else 0

        self.edit_start.setText(f"{self.canvas.start[0]},{self.canvas.start[1]}")
        self.edit_goal.setText(f"{self.canvas.goal[0]},{self.canvas.goal[1]}")
        self.canvas.update()
        self.lbl_mon_status.setText("Новий лабіринт згенеровано.")

    def on_swap_start_goal(self):
        self.on_reset_search()
        self.canvas.start, self.canvas.goal = self.canvas.goal, self.canvas.start
        self.edit_start.setText(f"{self.canvas.start[0]},{self.canvas.start[1]}")
        self.edit_goal.setText(f"{self.canvas.goal[0]},{self.canvas.goal[1]}")
        self.canvas.update()
        self.lbl_mon_status.setText("Старт і ціль поміняно місцями.")

    def get_neighbors(self, r, c):
        op_idx = self.combo_op.currentIndex()
        deltas = []

        if op_idx == 0:  # Ортогональний
            deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        elif op_idx == 1:  # Діагональний
            deltas = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        elif op_idx == 2:  # Комбінований
            deltas = [(-1, 0), (1, 0), (0, -1), (0, 1),
                      (-1, -1), (-1, 1), (1, -1), (1, 1)]

        neighbors = []
        for dr, dc in deltas:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.canvas.rows and 0 <= nc < self.canvas.cols:
                if self.canvas.grid[nr][nc] != -1:
                    if abs(dr) == 1 and abs(dc) == 1:
                        if self.canvas.grid[r + dr][c] == -1 and self.canvas.grid[r][c + dc] == -1:
                            continue
                    neighbors.append((nr, nc))
        return neighbors

    def init_search_structures(self):
        self.canvas.reset_search_visuals()
        self.queue_a.clear()
        self.queue_b.clear()
        self.dist_a.clear()
        self.dist_b.clear()
        self.parent_a.clear()
        self.parent_b.clear()

        s = self.canvas.start
        g = self.canvas.goal

        self.queue_a.append(s)
        self.dist_a[s] = 0
        self.parent_a[s] = None
        self.canvas.visited_a[s] = 0
        self.canvas.front_a.add(s)

        self.queue_b.append(g)
        self.dist_b[g] = 0
        self.parent_b[g] = None
        self.canvas.visited_b[g] = 0
        self.canvas.front_b.add(g)

        self.meet_node = None
        self.cycles_count = 0
        self.expanded_a_count = 0
        self.expanded_b_count = 0
        self.search_elapsed_time = 0.0

    def on_start_search(self):
        if self.is_running:
            return
        if not self.queue_a and not self.meet_node:
            self.init_search_structures()

        self.is_running = True
        self.lbl_mon_status.setText("Пошук триває...")
        self.anim_timer.start(self.slider_speed.value())

    def on_pause_search(self):
        self.is_running = False
        self.anim_timer.stop()
        self.lbl_mon_status.setText("Пошук призупинено.")

    def on_reset_search(self):
        self.is_running = False
        self.anim_timer.stop()
        self.canvas.reset_search_visuals()
        self.queue_a.clear()
        self.queue_b.clear()
        self.dist_a.clear()
        self.dist_b.clear()
        self.parent_a.clear()
        self.parent_b.clear()
        self.meet_node = None
        self.cycles_count = 0
        self.expanded_a_count = 0
        self.expanded_b_count = 0
        self.search_elapsed_time = 0.0
        self.lbl_mon_cycles.setText("Циклів: 0")
        self.lbl_mon_exp.setText("Розкрито (A+B): 0 + 0 = 0")
        self.lbl_mon_status.setText("Статус: Готовий до запуску")
        self.canvas.update()

    def on_step_search(self):
        if not self.queue_a and not self.meet_node:
            self.init_search_structures()
        self._step_animation()

    def _step_animation(self):
     
        if not self.queue_a or not self.queue_b:
            self.on_pause_search()
            self.lbl_mon_status.setText("Шлях не знайдено!")
            self.finalize_search(found=False, pure_time_ms=self.search_elapsed_time * 1000.0)
            return

        t_start = time.perf_counter()
        self.cycles_count += 1
        found = False


        if self.queue_a:
            curr_a = self.queue_a.popleft()
            self.expanded_a_count += 1
            if curr_a in self.canvas.front_a:
                self.canvas.front_a.remove(curr_a)

            for nxt in self.get_neighbors(*curr_a):
                if nxt not in self.dist_a:
                    self.dist_a[nxt] = self.dist_a[curr_a] + 1
                    self.parent_a[nxt] = curr_a
                    self.canvas.visited_a[nxt] = self.dist_a[nxt]
                    self.canvas.front_a.add(nxt)
                    self.queue_a.append(nxt)

                if nxt in self.dist_b:
                    self.meet_node = nxt
                    found = True
                    break


        if not found and self.queue_b:
            curr_b = self.queue_b.popleft()
            self.expanded_b_count += 1
            if curr_b in self.canvas.front_b:
                self.canvas.front_b.remove(curr_b)

            for nxt in self.get_neighbors(*curr_b):
                if nxt not in self.dist_b:
                    self.dist_b[nxt] = self.dist_b[curr_b] + 1
                    self.parent_b[nxt] = curr_b
                    self.canvas.visited_b[nxt] = self.dist_b[nxt]
                    self.canvas.front_b.add(nxt)
                    self.queue_b.append(nxt)

                if nxt in self.dist_a:
                    self.meet_node = nxt
                    found = True
                    break

        t_end = time.perf_counter()
        self.search_elapsed_time += (t_end - t_start)

        if found:
            self.finalize_search(found=True, pure_time_ms=self.search_elapsed_time * 1000.0)
            return

        self.lbl_mon_cycles.setText(f"Циклів: {self.cycles_count}")
        self.lbl_mon_exp.setText(f"Розкрито (A+B): {self.expanded_a_count} + {self.expanded_b_count} = {self.expanded_a_count + self.expanded_b_count}")
        self.canvas.update()

    def finalize_search(self, found, pure_time_ms=0.0):
        self.is_running = False
        self.anim_timer.stop()

        path = []
        if found and self.meet_node:
            self.canvas.meet_node = self.meet_node

            curr = self.meet_node
            path_a = []
            while curr is not None:
                path_a.append(curr)
                curr = self.parent_a.get(curr)
            path_a.reverse()

            curr = self.parent_b.get(self.meet_node)
            path_b = []
            while curr is not None:
                path_b.append(curr)
                curr = self.parent_b.get(curr)

            path = path_a + path_b
            self.canvas.final_path = path

        self.canvas.update()

        free_c = sum(row.count(0) for row in self.canvas.grid)
        wall_c = sum(row.count(-1) for row in self.canvas.grid)

        metrics = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "found": found,
            "rows": self.canvas.rows,
            "cols": self.canvas.cols,
            "free_cells": free_c,
            "walls": wall_c,
            "operator": self.combo_op.currentText(),
            "start": self.canvas.start,
            "goal": self.canvas.goal,
            "meet_node": self.meet_node,
            "path_length": len(path) - 1 if path else 0,
            "path_cells": len(path),
            "cycles": self.cycles_count,
            "expanded": self.expanded_a_count + self.expanded_b_count,
            "expanded_a": self.expanded_a_count,
            "expanded_b": self.expanded_b_count,
            "marked": len(self.dist_a) + len(self.dist_b),
            "marked_a": len(self.dist_a),
            "marked_b": len(self.dist_b),
            "time_ms": pure_time_ms,
            "path": path
        }

        mat_a = [[self.dist_a.get((r, c), -1 if self.canvas.grid[r][c] == -1 else 0)
                  for c in range(self.canvas.cols)] for r in range(self.canvas.rows)]
        mat_b = [[self.dist_b.get((r, c), -1 if self.canvas.grid[r][c] == -1 else 0)
                  for c in range(self.canvas.cols)] for r in range(self.canvas.rows)]

        self.export_results_csv(metrics)

        dlg = WaveResultDialog(metrics, mat_a, mat_b, self)
        dlg.exec_()

    def on_instant_search(self):
    
        self.on_reset_search()
        self.init_search_structures()

        start_time = time.perf_counter()
        found = False

        while self.queue_a and self.queue_b:
            self.cycles_count += 1

            curr_a = self.queue_a.popleft()
            self.expanded_a_count += 1
            for nxt in self.get_neighbors(*curr_a):
                if nxt not in self.dist_a:
                    self.dist_a[nxt] = self.dist_a[curr_a] + 1
                    self.parent_a[nxt] = curr_a
                    self.canvas.visited_a[nxt] = self.dist_a[nxt]
                    self.queue_a.append(nxt)

                if nxt in self.dist_b:
                    self.meet_node = nxt
                    found = True
                    break
            if found:
                break

            curr_b = self.queue_b.popleft()
            self.expanded_b_count += 1
            for nxt in self.get_neighbors(*curr_b):
                if nxt not in self.dist_b:
                    self.dist_b[nxt] = self.dist_b[curr_b] + 1
                    self.parent_b[nxt] = curr_b
                    self.canvas.visited_b[nxt] = self.dist_b[nxt]
                    self.queue_b.append(nxt)

                if nxt in self.dist_a:
                    self.meet_node = nxt
                    found = True
                    break
            if found:
                break

        end_time = time.perf_counter()
        pure_time_ms = (end_time - start_time) * 1000.0

        self.finalize_search(found=found, pure_time_ms=pure_time_ms)

    def export_results_csv(self, metrics):
        os.makedirs("results", exist_ok=True)
        csv_file = os.path.join("results", "wave_results.csv")
        file_exists = os.path.isfile(csv_file)

        fieldnames = [
            "timestamp", "rows", "cols", "operator", "start", "goal",
            "found", "path_length", "path_cells", "cycles",
            "expanded", "expanded_a", "expanded_b",
            "marked", "marked_a", "marked_b", "meet_node", "time_ms"
        ]

        with open(csv_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "timestamp": metrics["timestamp"],
                "rows": metrics["rows"],
                "cols": metrics["cols"],
                "operator": metrics["operator"],
                "start": str(metrics["start"]),
                "goal": str(metrics["goal"]),
                "found": metrics["found"],
                "path_length": metrics["path_length"],
                "path_cells": metrics["path_cells"],
                "cycles": metrics["cycles"],
                "expanded": metrics["expanded"],
                "expanded_a": metrics["expanded_a"],
                "expanded_b": metrics["expanded_b"],
                "marked": metrics["marked"],
                "marked_a": metrics["marked_a"],
                "marked_b": metrics["marked_b"],
                "meet_node": str(metrics["meet_node"]),
                "time_ms": f"{metrics['time_ms']:.4f}"
            })


def main():
    app = QApplication(sys.argv)
    window = WavePyQtModernWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

