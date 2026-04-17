import pytest
from unittest.mock import AsyncMock, MagicMock
import discord

from Webscrape.dialogue import ConfirmView, defaultView


def make_interaction():
    interaction = MagicMock()
    interaction.message = MagicMock()
    interaction.message.id = 123
    interaction.followup = MagicMock()
    interaction.followup.edit_message = AsyncMock()
    interaction.edit_original_response = AsyncMock()
    return interaction


@pytest.mark.asyncio
async def test_confirm_view_on_cancel_sets_false():
    view = ConfirmView()
    interaction = make_interaction()

    await view.on_cancel(interaction)

    assert view.value is False


@pytest.mark.asyncio
async def test_confirm_view_on_response_disables_buttons_and_edits_message():
    view = ConfirmView()
    interaction = make_interaction()

    await view.on_response(interaction)

    for button in view.children:
        assert button.disabled is True
    interaction.followup.edit_message.assert_awaited_once_with(
        interaction.message.id,
        view=view,
    )


@pytest.mark.asyncio
async def test_default_view_on_response_disables_items_and_edits_original_response():
    view = defaultView()
    view.add_item(discord.ui.Button(label="Test"))
    interaction = make_interaction()

    await view.on_response(interaction)

    for item in view.children:
        assert item.disabled is True
    interaction.edit_original_response.assert_awaited_once_with(view=view)


@pytest.mark.asyncio
async def test_default_view_on_timeout_has_no_interaction_arg():
    view = defaultView()
    view.add_item(discord.ui.Button(label="Test"))

    # Regression check: this should not require an interaction argument.
    await view.on_timeout()

    for item in view.children:
        assert item.disabled is True