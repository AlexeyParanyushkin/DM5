"""ЛР2, вариант 1."""
import argparse
import itertools
import re

SYSTEMS = {"C2": (0, 1), "K3": (0, 0.5, 1), "L3": (0, 0.5, 1)}
FORMULAS = [
    "(p -> q) | (q -> p)",
    "((p -> q) -> p) -> p",
    "(p & !p) | q",
    "(p & !p) & q",
    "((p -> q) & (q -> r)) -> (p -> r)",
]
RELATIONS = [
    (["p | q", "p -> r", "q -> r", "r -> s", "s -> t"], "t"),
    (["p -> q", "p -> r", "(q & r) -> s", "s -> t", "t -> u"], "!p | u"),
    (["p | q", "p -> r", "q -> s", "r -> t", "s -> t"], "t & (p | !p)"),
    (["p | q", "p -> r", "q -> s", "(r | s) -> t", "s -> u"], "t -> u"),
]


class Parser:
    def __init__(self, source):
        self.tokens = []
        pattern = re.compile(r"\s+|->|[→⊃¬!~∧&∨|()]|[A-Za-z][A-Za-z0-9_]*|[01]")
        aliases = {"->": "→", "⊃": "→", "!": "¬", "~": "¬", "&": "∧", "|": "∨"}
        pos = 0
        while pos < len(source):
            match = pattern.match(source, pos)
            if not match:
                raise ValueError(f"Недопустимый символ в позиции {pos + 1}: {source[pos]!r}")
            token = match.group()
            if not token.isspace():
                self.tokens.append(aliases.get(token, token))
            pos = match.end()
        self.pos = 0

    def take(self, token):
        if self.pos < len(self.tokens) and self.tokens[self.pos] == token:
            self.pos += 1
            return True
        return False

    # разбор начинается с самой слабой операции
    def parse(self):
        tree = self.implication()
        if self.pos != len(self.tokens):
            raise ValueError(f"Лишний элемент: {self.tokens[self.pos]}")
        return tree

    def implication(self):
        tree = self.disjunction()

        while self.take("→"):
            tree = ("→", tree, self.disjunction())

        return tree

    def disjunction(self):
        tree = self.conjunction()
        while self.take("∨"):
            tree = ("∨", tree, self.conjunction())
        return tree

    def conjunction(self):
        tree = self.atom()
        while self.take("∧"):
            tree = ("∧", tree, self.atom())
        return tree

    def atom(self):  # разбор аргумента операции: переменная, константа, ф-ла в скобках
        if self.take("¬"):
            return ("¬", self.atom())
        if self.take("("):
            tree = self.implication()
            if not self.take(")"):
                raise ValueError("Ожидалась закрывающая скобка")
            return tree
        if self.pos >= len(self.tokens):
            raise ValueError("Ожидалась переменная, константа или подформула")
        token = self.tokens[self.pos]
        self.pos += 1
        if token in ("f", "0", "1"):
            return ("const", int(token == "1"))
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", token):
            return ("var", token)
        raise ValueError(f"Неожиданный элемент: {token}")


def parse(source):
    return Parser(source).parse()


def variables(tree):  # множество переменных
    if tree[0] == "var":
        return {tree[1]}
    if tree[0] == "const":
        return set()
    return set().union(*(variables(child) for child in tree[1:]))


def pretty(tree):
    op = tree[0]
    if op == "var":
        return tree[1]
    if op == "const":
        return "f" if tree[1] == 0 else "1"
    if op == "¬":
        return "¬" + pretty(tree[1])
    return f"({pretty(tree[1])} {op} {pretty(tree[2])})"


def evaluate(tree, assignment, system):
    op = tree[0]
    if op == "const":
        return tree[1]  # возврат значения константы
    if op == "var":
        return assignment[tree[1]]  # возврат значения из словаря
    a = evaluate(tree[1], assignment, system)  # рекурсивное вычисление первого аргумента операции
    if op == "¬":
        return 1 - a  # возврат отрицания
    b = evaluate(tree[2], assignment, system)  # вычисление второго аргумента
    if op == "∧":
        return min(a, b)  # конъюнкция
    if op == "∨":
        return max(a, b)  # дизъюнкция
    return min(1, 1 - a + b) if system == "L3" else max(1 - a, b)  # импликация


def interpretations(names, system):  # генерация всех возможных оценок переменных
    for values in itertools.product(SYSTEMS[system], repeat=len(names)):  # все комбинации в заданной логике
        yield dict(zip(names, values))  # возврат словарей по одному


def analyze(tree, system):  # проверка формулы на всех значениях
    names = sorted(variables(tree))

    # для каждой оценки вычисляет формулу и сохраняет пару «оценка — результат».
    rows = [(a, evaluate(tree, a, system)) for a in interpretations(names, system)]
    values = [value for _, value in rows]  # получение результатов
    return {
        "rows": rows,
        "valid": all(v == 1 for v in values),  # общезначимость
        "satisfiable": any(v == 1 for v in values),  # выполнимость
        "identically_false": all(v == 0 for v in values),  # тождественная ложность
        "counterexample": next(((a, v) for a, v in rows if v != 1), None),  # первая ложь
    }


def entails(premises, conclusion, system):
    """
    - premises — список деревьев посылок;
    - conclusion — дерево заключения;
    - system — выбранная логика.
    """
    names = sorted(
        set().union(variables(conclusion), *(variables(p) for p in premises)))  # все переменные из посылок и заключения
    models = 0
    counterexample = None
    for assignment in interpretations(names, system):  # перебор всех оценок
        values = [evaluate(p, assignment, system) for p in premises]  # значения посылок
        value = evaluate(conclusion, assignment, system)  # значение заключения
        if all(v == 1 for v in values):  # все ли посылки истинны
            models += 1
            if value != 1 and counterexample is None:  # сохранение контрпримера
                counterexample = (assignment, values, value)
    return {"holds": counterexample is None, "models": models, "counterexample": counterexample}


def fmt(value):  # формирование вывода: истинность из числа в строку
    return "1/2" if value == 0.5 else str(int(value))


def describe(assignment):  # формирование вывода: вывод переменных в виде "p=1, q=1/2"
    return ", ".join(f"{k}={fmt(v)}" for k, v in assignment.items()) or "без переменных"


def table(headers, rows):  # формирование вывода
    rows = [[str(value) for value in row] for row in rows]
    widths = [max(len(str(h)), *(len(row[i]) for row in rows)) for i, h in enumerate(headers)]
    print(" | ".join(str(h).ljust(w) for h, w in zip(headers, widths)))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(" | ".join(v.ljust(w) for v, w in zip(row, widths)))


def show_formula(tree, systems, full_table=True, assignment=None):  # исследование ф-лы и вывод результатов
    """
    tree - Дерево формулы
    systems	- Список выбранных логик
    full_table - Печатать ли таблицу истинности
    assignment - Заданная оценка; None означает исследование всех оценок
    """
    print("Формула:", pretty(tree))
    names = sorted(variables(tree))
    results = {}
    for system in systems:  # обработка каждой выбранной логики
        print(f"\n{system}:")
        if assignment is not None:  # проверка конкретной оценки
            if set(assignment) != set(names):
                raise ValueError("Нужно задать ровно эти переменные: " + ", ".join(names))
            if any(v not in SYSTEMS[system] for v in assignment.values()):
                print("Заданная оценка недопустима для этой логики.")
                continue
            results[system] = evaluate(tree, assignment, system)
            print("Значение:", fmt(results[system]))
            continue
        result = analyze(tree, system)
        results[system] = result
        if full_table:
            table(names + ["F"], [[*(fmt(a[n]) for n in names), fmt(v)] for a, v in result["rows"]])
        print("Общезначима:", result["valid"])
        print("Выполнима:", result["satisfiable"])
        print("Невыполнима:", not result["satisfiable"])
        print("Тождественно ложна:", result["identically_false"])
        if result["counterexample"]:
            a, v = result["counterexample"]
            print(f"Контрпример общезначимости: {describe(a)}; F={fmt(v)}")
    if len(results) > 1:
        if assignment is not None:
            print("\nЗначения совпадают:", len(set(results.values())) == 1)
        else:
            for left, right in itertools.combinations(results, 2):  # попарное сравнение результатов
                domain = sorted(set(SYSTEMS[left]) & set(SYSTEMS[right]))
                equal = all(evaluate(tree, dict(zip(names, v)), left) == evaluate(tree, dict(zip(names, v)), right)
                            for v in itertools.product(domain, repeat=len(names)))
                props = ("valid", "satisfiable", "identically_false")
                same = all(results[left][p] == results[right][p] for p in props)
                print(f"\n{left} / {right}: значения на общих оценках совпадают: {equal}; свойства совпадают: {same}")


def show_relation(premises, conclusion, systems):  # результат проверки следования
    """
    premises: деревья посылок
    conclusion: дерево заключения
    systems: список логик
    """
    print(", ".join(map(pretty, premises)), "|-", pretty(conclusion))  # само отношение
    for system in systems:
        r = entails(premises, conclusion, system)
        print(f"{system}: следование {r['holds']}; общих моделей посылок: {r['models']}")
        if not r["models"]:
            print("Нет интерпретаций, где все посылки равны 1; следование выполняется вакуозно.")
        if r["counterexample"]:
            a, values, v = r["counterexample"]
            print(f"Контрпример: {describe(a)}; посылки: {list(map(fmt, values))}; вывод: {fmt(v)}")


def variant(full_table=True):  # проверка формул из варианта
    for i, source in enumerate(FORMULAS, 1):
        print(f"\nF{i}")
        show_formula(parse(source), list(SYSTEMS), full_table)
    for i, (sources, target) in enumerate(RELATIONS, 1):
        print(f"\nR{i}")
        show_relation(list(map(parse, sources)), parse(target), list(SYSTEMS))


def input_systems():
    name = input("Логика C2 / K3 / L3 / ALL: ").strip().upper()
    if name == "ALL":
        return list(SYSTEMS)
    if name not in SYSTEMS:
        raise ValueError("Неизвестная логика")
    return [name]


def interactive():  # вывод меню
    while True:
        print("\n1 — формула; 2 — следование; 3 — проверка варианта; 0 — выход")
        try:
            choice = input("Режим: ").strip()
            if choice == "0":
                print("Завершено по команде пользователя")
                exit(0)
            if choice == "1":
                tree = parse(input("Формула: "))
                systems = input_systems()
                mode = input("1 — заданная оценка; 2 — все оценки: ").strip()
                if mode not in ("1", "2"):
                    raise ValueError("Неизвестный режим оценок")
                assignment = None
                if mode == "1":
                    assignment = {}
                    for name in sorted(variables(tree)):
                        raw = input(f"{name} = ").strip().replace(",", ".")
                        assignment[name] = 0.5 if raw == "1/2" else float(raw)
                show_formula(tree, systems, assignment=assignment)
            elif choice == "2":
                sources = input("Посылки через ; (пусто — без посылок): ").strip()
                premises = [parse(s) for s in sources.split(";")] if sources else []
                conclusion = parse(input("Вывод: "))
                show_relation(premises, conclusion, input_systems())
            elif choice == "3":
                variant()
            else:
                print("Неизвестный режим")
        except (ValueError, RecursionError) as error:
            print("Ошибка:", error)
        except (EOFError, KeyboardInterrupt):
            print("\nВыход")
            return


cli = argparse.ArgumentParser(description=__doc__)
cli.add_argument("--variant", action="store_true", help="проверить вариант 1")
cli.add_argument("--brief", action="store_true", help="не выводить таблицы в режиме --variant")
args = cli.parse_args()
if args.variant:
    variant(not args.brief)
else:
    interactive()

