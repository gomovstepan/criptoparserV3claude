import json
import sys

def deduplicate_logs(input_file):
    seen = set()
    unique_entries = []

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Удаляем временную метку для сравнения
                # Если хотите сохранить время, скопируйте entry в copy
                # entry = entry.copy()
                entry.pop('timestamp', None)  # или 'time', '@timestamp' и т.д.

                # Создаём каноническое представление (сортируем ключи)
                key = json.dumps(entry, sort_keys=True, ensure_ascii=False)
                errors = []
                if key not in seen:
                    if entry['level'] !='info' and entry['error'] not in errors:
                        seen.add(key)
                        unique_entries.append(entry)   # сохраняем оригинал с временем
                    else:
                        # print(entry)
                        if entry['level'] !='info':
                            errors.append(entry['error'])
            except json.JSONDecodeError as e:
                print(f"Ошибка в строке: {e}", file=sys.stderr)

    # Выводим уникальные записи в красивом формате (или компактном)
    for entry in unique_entries:
        # print(json.dumps(entry, indent=2, ensure_ascii=False))
        print(entry)  # разделитель

if __name__ == "__main__":
    deduplicate_logs('/var/projects/criptoparserV3claude/logs/collector.log')