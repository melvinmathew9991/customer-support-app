from customer_support_app.domain.chat import MessageHistory, Role


def test_add_message_helpers_tag_the_correct_role():
    history = MessageHistory([])

    history.add_system_message("sys note")
    history.add_user_message("hi")
    history.add_assistant_message("hello")

    assert history.messages == [
        {"content": "sys note", "role": "system"},
        {"content": "hi", "role": "user"},
        {"content": "hello", "role": "assistant"},
    ]


def test_role_based_history_filters_by_role():
    history = MessageHistory([])
    history.add_user_message("first")
    history.add_assistant_message("reply")
    history.add_user_message("second")

    user_messages = history.role_based_history(Role.USER)

    assert [m["content"] for m in user_messages] == ["first", "second"]


def test_model_input_uses_last_user_message_and_excludes_it_from_history():
    history = MessageHistory([])
    history.add_assistant_message("Hi, how can I help?")
    history.add_user_message("I need help with X")

    model_input = history.model_input()

    assert model_input.input == "\nuser: I need help with X"
    assert model_input.history == "\nassistant: Hi, how can I help?"


def test_str_formats_every_message_in_order():
    history = MessageHistory([])
    history.add_user_message("hi")
    history.add_assistant_message("hello")

    assert str(history) == "\nuser: hi\nassistant: hello"
