from dataclasses import dataclass
from typing import Optional


# ============================================================
# АБСТРАКТНОЕ СИНТАКСИЧЕСКОЕ ДЕРЕВО
# ============================================================

@dataclass(frozen=True)
class Node:
    kind: str
    value: str = ""
    left: Optional["Node"] = None
    right: Optional["Node"] = None


def Variable(name: str) -> Node:
    return Node(
        kind="var",
        value=name
    )


def Implication(left: Node, right: Node) -> Node:
    return Node(
        kind="imp",
        left=left,
        right=right
    )


# ============================================================
# ПЕЧАТЬ ФОРМУЛЫ
# ============================================================

def pretty_formula(node: Node) -> str:
    """
    Преобразует AST обратно в строку.

    Сложные части заключаются в скобки так,
    чтобы структура формулы не терялась.
    """

    if node.kind == "var":
        return node.value

    left = pretty_formula(node.left)
    right = pretty_formula(node.right)

    if node.left.kind == "imp":
        left = "(" + left + ")"

    if node.right.kind == "imp":
        right = "(" + right + ")"

    return f"{left} ⊃ {right}"


# ============================================================
# ПАРСЕР
# ============================================================

class ParserError(Exception):
    pass


class Parser:

    def __init__(self, text: str):
        self.text = text
        self.pos = 0

    def skip_spaces(self):
        while (
                self.pos < len(self.text)
                and self.text[self.pos].isspace()
        ):
            self.pos += 1

    def current_char(self) -> Optional[str]:
        self.skip_spaces()

        if self.pos >= len(self.text):
            return None

        return self.text[self.pos]

    def parse(self) -> Node:
        self.skip_spaces()

        if self.pos >= len(self.text):
            raise ParserError("Пустая строка.")

        result = self.parse_implication()

        self.skip_spaces()

        if self.pos != len(self.text):
            char = self.text[self.pos]

            raise ParserError(
                f"Неожиданный символ '{char}' "
                f"в позиции {self.pos + 1}."
            )

        return result

    def parse_implication(self) -> Node:
        """
        Импликация правоассоциативна:

        p ⊃ q ⊃ r

        разбирается как

        p ⊃ (q ⊃ r)
        """

        left = self.parse_primary()

        self.skip_spaces()

        if self.current_char() == "⊃":
            self.pos += 1

            right = self.parse_implication()

            return Implication(
                left,
                right
            )

        return left

    def parse_primary(self) -> Node:
        self.skip_spaces()

        if self.pos >= len(self.text):
            raise ParserError(
                "Ожидалась пропозициональная переменная "
                "или формула в скобках."
            )

        char = self.text[self.pos]

        # ----------------------------------------------------
        # Круглые скобки
        # ----------------------------------------------------

        if char == "(":
            self.pos += 1

            self.skip_spaces()

            if self.current_char() == ")":
                raise ParserError(
                    "Пустые круглые скобки."
                )

            node = self.parse_implication()

            self.skip_spaces()

            if (
                    self.pos >= len(self.text)
                    or self.text[self.pos] != ")"
            ):
                raise ParserError(
                    "Ожидалась закрывающая круглая скобка ')'."
                )

            self.pos += 1

            return node

        # ----------------------------------------------------
        # Квадратные скобки
        # ----------------------------------------------------

        if char == "[":
            self.pos += 1

            self.skip_spaces()

            if self.current_char() == "]":
                raise ParserError(
                    "Пустые квадратные скобки."
                )

            node = self.parse_implication()

            self.skip_spaces()

            if (
                    self.pos >= len(self.text)
                    or self.text[self.pos] != "]"
            ):
                raise ParserError(
                    "Ожидалась закрывающая квадратная скобка ']'."
                )

            self.pos += 1

            return node

        # ----------------------------------------------------
        # Пропозициональная переменная
        #
        # Ожидается ровно один латинский символ:
        # p, q, r, s и т.д.
        # ----------------------------------------------------

        if char.isascii() and char.isalpha():
            self.pos += 1

            return Variable(char)

        # ----------------------------------------------------
        # Ошибки
        # ----------------------------------------------------

        if char == ")":
            raise ParserError(
                "Лишняя закрывающая круглая скобка ')'."
            )

        if char == "]":
            raise ParserError(
                "Лишняя закрывающая квадратная скобка ']'."
            )

        if char == "⊃":
            raise ParserError(
                "Оператор '⊃' не может находиться "
                "в этом месте."
            )

        raise ParserError(
            f"Недопустимый символ '{char}' "
            f"в позиции {self.pos + 1}."
        )


def parse_formula(text: str) -> Node:
    return Parser(text).parse()


# ============================================================
# СРАВНЕНИЕ ДЕРЕВЬЕВ
# ============================================================

def trees_equal(a: Node, b: Node) -> bool:
    if a.kind != b.kind:
        return False

    if a.kind == "var":
        return a.value == b.value

    return (
            trees_equal(a.left, b.left)
            and trees_equal(a.right, b.right)
    )


# ============================================================
# АКСИОМЫ
# ============================================================

AXIOM_SCHEMAS = [

    (
        "1",
        parse_formula(
            "p ⊃ (q ⊃ p)"
        )
    ),

    (
        "2",
        parse_formula(
            "(s ⊃ (p ⊃ q)) ⊃ "
            "((s ⊃ p) ⊃ (s ⊃ q))"
        )
    ),

    (
        "3",
        parse_formula(
            "(((p ⊃ f)) ⊃ f) ⊃ p"
        )
    )
]


# ============================================================
# СОПОСТАВЛЕНИЕ СХЕМЫ АКСИОМЫ
# ============================================================

def match_schema(
        pattern: Node,
        actual: Node,
        mapping: Optional[dict[str, Node]] = None
) -> Optional[dict[str, Node]]:
    """
    Проверяет, является ли actual экземпляром схемы pattern.

    Переменная в схеме может соответствовать
    абсолютно любой формуле.

    Например:

        p ⊃ (q ⊃ p)

    и

        (r ⊃ s) ⊃ (q ⊃ (r ⊃ s))

    дают:

        p -> (r ⊃ s)
        q -> q
    """

    if mapping is None:
        mapping = {}

    # --------------------------------------------------------
    # Переменная схемы
    # --------------------------------------------------------

    if pattern.kind == "var":

        name = pattern.value

        # Переменная встречается впервые:
        # запоминаем, какой формуле она соответствует.
        if name not in mapping:
            mapping[name] = actual
            return mapping

        # Повторное вхождение той же переменной
        # обязано соответствовать точно той же формуле.
        if trees_equal(
                mapping[name],
                actual
        ):
            return mapping

        return None

    # --------------------------------------------------------
    # Оба узла должны иметь одинаковую структуру
    # --------------------------------------------------------

    if actual.kind != pattern.kind:
        return None

    # --------------------------------------------------------
    # Рекурсивная проверка левой части
    # --------------------------------------------------------

    mapping = match_schema(
        pattern.left,
        actual.left,
        mapping
    )

    if mapping is None:
        return None

    # --------------------------------------------------------
    # Рекурсивная проверка правой части
    # --------------------------------------------------------

    mapping = match_schema(
        pattern.right,
        actual.right,
        mapping
    )

    return mapping


def is_axiom_instance(
        formula: Node
):
    """
    Возвращает:

        (True, номер_аксиомы)

    если formula является экземпляром аксиомы,

    иначе:

        (False, None)
    """

    for number, schema in AXIOM_SCHEMAS:

        mapping = match_schema(
            schema,
            formula
        )

        if mapping is not None:
            return True, number

    return False, None


# ============================================================
# ИНСТАНЦИАЦИЯ СХЕМЫ
# ============================================================

def instantiate_schema(
        node: Node,
        mapping: dict[str, Node]
) -> Node:
    """
    Подставляет конкретные формулы в схему.
    """

    if node.kind == "var":

        if node.value in mapping:
            return mapping[node.value]

        return node

    return Implication(
        instantiate_schema(
            node.left,
            mapping
        ),
        instantiate_schema(
            node.right,
            mapping
        )
    )


# ============================================================
# ПОДСТАНОВКА
# ============================================================

def substitute(
        node: Node,
        variable: str,
        replacement: Node
) -> Node:
    """
    Выполняет одновременную замену ВСЕХ вхождений
    переменной variable в node на replacement.

    Важно:
    содержимое replacement дополнительно не обрабатывается.
    Это именно [B/b]A.
    """

    if node.kind == "var":

        if node.value == variable:
            return replacement

        return node

    return Implication(
        substitute(
            node.left,
            variable,
            replacement
        ),
        substitute(
            node.right,
            variable,
            replacement
        )
    )


# ============================================================
# ПРАВИЛО β
# ============================================================

def find_beta_substitution(
        source: Node,
        target: Node
):
    """
    Строгая проверка правила β:

             ⊢ A
        -------------
        ⊢ [B/b]A

    source = A
    target = [B/b]A

    b — одна пропозициональная переменная
    B — произвольная формула

    Возвращает:

        (b, B)

    либо None.
    """

    # --------------------------------------------------------
    # Получаем список переменных, встречающихся в A.
    # --------------------------------------------------------

    variables = set()

    def collect_variables(node: Node):

        if node.kind == "var":
            variables.add(node.value)
            return

        collect_variables(node.left)
        collect_variables(node.right)

    collect_variables(source)

    # --------------------------------------------------------
    # Пробуем каждую переменную в качестве b.
    # --------------------------------------------------------

    for variable in variables:

        replacement: Optional[Node] = None

        def match(
                source_node: Node,
                target_node: Node
        ) -> bool:
            nonlocal replacement

            # ------------------------------------------------
            # Нашли заменяемую переменную b
            # ------------------------------------------------

            if (
                    source_node.kind == "var"
                    and source_node.value == variable
            ):

                # Первое вхождение:
                # определяем B.
                if replacement is None:
                    replacement = target_node
                    return True

                # Все остальные вхождения b должны
                # содержать абсолютно тот же B.
                return trees_equal(
                    replacement,
                    target_node
                )

            # ------------------------------------------------
            # Остальные обычные переменные
            # не должны меняться.
            # ------------------------------------------------

            if source_node.kind == "var":
                return (
                        target_node.kind == "var"
                        and source_node.value
                        == target_node.value
                )

            # ------------------------------------------------
            # Если в A была импликация,
            # в target тоже должна быть импликация.
            # ------------------------------------------------

            if target_node.kind != "imp":
                return False

            return (
                    match(
                        source_node.left,
                        target_node.left
                    )
                    and
                    match(
                        source_node.right,
                        target_node.right
                    )
            )

        # ----------------------------------------------------
        # Проверяем структуру.
        # ----------------------------------------------------

        if not match(source, target):
            continue

        # Замена должна реально присутствовать.
        if replacement is None:
            continue

        # ----------------------------------------------------
        # Финальная проверка непосредственно операцией
        # [B/b]A.
        # ----------------------------------------------------

        substituted = substitute(
            source,
            variable,
            replacement
        )

        if trees_equal(
                substituted,
                target
        ):
            return variable, replacement

    return None


# ============================================================
# ДОСТУПНОСТЬ ФОРМУЛЫ
# ============================================================

def is_available_formula(
        formula: Node,
        proved: list[Node]
) -> bool:
    """
    Формула доступна для использования как посылка,
    если она:

    1. уже была выведена;
    ИЛИ
    2. является экземпляром аксиомы.
    """

    # Уже выведена
    for item in proved:

        if trees_equal(
                item,
                formula
        ):
            return True

    # Является аксиомой
    axiom, _ = is_axiom_instance(
        formula
    )

    return axiom


# ============================================================
# MODUS PONENS
# ============================================================

def find_mp(
        target: Node,
        proved: list[Node]
):
    """
    Проверяет правило modus ponens:

           A ⊃ B
           A
           ----
             B

    где B = target.

    Обе посылки должны уже находиться
    среди ранее выведенных формул.
    """

    for implication_formula in proved:

        # Ищем формулу вида A ⊃ B
        if implication_formula.kind != "imp":
            continue

        antecedent = implication_formula.left
        consequent = implication_formula.right

        # Правая часть должна совпадать с target
        if not trees_equal(
                consequent,
                target
        ):
            continue

        # Левая часть A тоже должна быть ранее выведена
        if is_available_formula(
                antecedent,
                proved
        ):
            return (
                antecedent,
                implication_formula
            )

    return None

# ============================================================
# ВЕРИФИКАТОР
# ============================================================

class Verifier:

    def __init__(self):
        self.proved: list[Node] = []

    def reset(self):
        self.proved.clear()

    def already_proved(
            self,
            formula: Node
    ) -> bool:

        return any(
            trees_equal(
                formula,
                item
            )
            for item in self.proved
        )

    def verify(
            self,
            formula: Node
    ) -> bool:

        # ====================================================
        # 1. АКСИОМА
        # ====================================================

        axiom, number = is_axiom_instance(
            formula
        )

        if axiom:

            if self.already_proved(
                    formula
            ):
                print(
                    "Эта формула уже была выведена ранее."
                )
                return True

            self.proved.append(
                formula
            )

            print(
                f"Формула {pretty_formula(formula)} "
                f"является экземпляром аксиомы {number}."
            )

            return True

        # ====================================================
        # 2. β
        #
        # ⊢ A
        # --------
        # ⊢ [B/b]A
        # ====================================================

        for source in self.proved:

            beta_result = find_beta_substitution(
                source,
                formula
            )

            if beta_result is not None:
                variable, replacement = beta_result

                self.proved.append(
                    formula
                )

                print(
                    f"Формула {pretty_formula(formula)} "
                    f"выводима из формулы "
                    f"{pretty_formula(source)} "
                    f"по правилу бета с подстановкой формулы "
                    f"{pretty_formula(replacement)} "
                    f"вместо переменной {variable}."
                )

                return True

        # ====================================================
        # 3. MP
        # ====================================================

        mp_result = find_mp(
            formula,
            self.proved
        )

        if mp_result is not None:
            antecedent, implication_formula = mp_result

            self.proved.append(
                formula
            )

            print(
                f"Формула {pretty_formula(formula)} "
                f"выводима из формул "
                f"{pretty_formula(implication_formula)} "
                f"и {pretty_formula(antecedent)} "
                f"по правилу modus ponens."
            )

            return True

        # ====================================================
        # 4. ФОРМУЛА НЕ ВЫВОДИМА
        # ====================================================

        print(
            f"Формула {pretty_formula(formula)} "
            f"не выводима из имеющихся аксиом "
            f"и предыдущих формул."
        )

        return False

    def show_proved(self):

        print()
        print("Выведенные формулы:")

        if not self.proved:
            print("  Список пуст.")
            return

        for i, formula in enumerate(
                self.proved,
                start=1
        ):
            print(
                f"  {i}. {pretty_formula(formula)}"
            )


# ============================================================
# СПРАВКА
# ============================================================

def print_help():
    print()
    print("Допустимые операции:")
    print("  ⊃  - импликация")

    print()
    print("Допустимые скобки:")
    print("  (...)")
    print("  [...]")

    print()
    print("Команды:")
    print("  /list - показать выведенные формулы")
    print("  /help - показать справку")
    print("  /exit - завершить программу")
    print("  /reset - начать новый тест, очистив выведенные формулы")

    print()
    print("Примеры п.п.ф.:")
    print("  p")
    print("  p ⊃ q")
    print("  p ⊃ (q ⊃ p)")
    print("  (p ⊃ q) ⊃ r")
    print("  [p ⊃ q] ⊃ r")

    print()


# ============================================================
# MAIN
# ============================================================

def main():
    verifier = Verifier()

    print("=" * 70)
    print("Лабораторная работа №1")
    print("Верификатор доказательств в исчислении высказываний")
    print("Вариант 1")
    print("=" * 70)

    print()
    print("Аксиомы:")

    print(
        "1) p ⊃ (q ⊃ p)"
    )

    print(
        "2) (s ⊃ (p ⊃ q)) ⊃ "
        "((s ⊃ p) ⊃ (s ⊃ q))"
    )

    print()
    print("Правила вывода:")
    print("  MP")
    print("  β")
    print()

    print_help()

    while True:

        try:
            user_input = input(
                "Введите формулу: "
            ).strip()

        except (
                EOFError,
                KeyboardInterrupt
        ):
            print()
            print(
                "Работа программы завершена."
            )
            break

        # ----------------------------------------------------
        # Команды
        # ----------------------------------------------------

        if user_input == "/exit":
            print(
                "Работа программы завершена."
            )
            break

        if user_input == "/reset":
            verifier.reset()
            print("Список выведенных формул очищен.")
            print()
            continue

        if user_input == "/list":
            verifier.show_proved()
            print()
            continue

        if user_input == "/help":
            print_help()
            continue

        # ----------------------------------------------------
        # Пустая строка
        # ----------------------------------------------------

        if not user_input:
            print(
                "Ошибка: пустая строка "
                "не является п.п.ф."
            )
            print()
            continue

        # ----------------------------------------------------
        # Синтаксический анализ
        # ----------------------------------------------------

        try:

            formula = parse_formula(
                user_input
            )

        except ParserError as error:

            print(
                "Ошибка: введенная строка "
                "не является п.п.ф."
            )

            print(
                f"Причина: {error}"
            )

            print()
            continue

        # ----------------------------------------------------
        # Верификация
        # ----------------------------------------------------

        verifier.verify(
            formula
        )

        print()


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    main()
