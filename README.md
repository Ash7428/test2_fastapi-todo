## Integration testing results

5 tests passed  
1 test reveals a bug (editing non-existing todo raises AttributeError)

Tests executed with:
```bash
pytest -v

main.py:64: in put_edit
    todo = update_todo(db, item_id, content)
...
models.py:30: in update_todo
    todo = get_todo(db, item_id)
>   todo.content = content
E   AttributeError: 'NoneType' object has no attribute 'content'
```
