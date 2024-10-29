"""
I'm writing this so I can send it to the Libby app team, in the hopes they'll
adapt it as their way of handling links in a text.

The problem I'm trying to address is: it's common for footnote links in an ebook
to be quite small and difficult to click on, e.g. a single superscript asterisk.
An asterisk is much smaller than my fingertip, and you can't zoom in, so it
often takes me up to 20 attempts to click on the footnote link. This comes with
other problems, e.g.: When a link appears near the edge of a page, misclicking
it results in a page turn, so I find myself rapidly turning the page back and
forth and muttering curse words.

It can't just be me.

I'm proposing a change to the code that handles touch input events and decides
what is being clicked on, specifically whether any button/link that's part of
the ebook content is being clicked. My suggestion, implemented in Python below,
behaves the same as the existing app code when the user accurately clicks a
link, but is more forgiving when they click *near* a link.
"""


import collections

from typing import Mapping, NamedTuple, Optional, TypeVar


# Pardon my overly fussy types, I can't help it.


class Point(NamedTuple):
    x: int
    y: int


class RectSize(NamedTuple):
    # Width and height must be both at least 1
    width: int
    height: int


class Rectangle(NamedTuple):
    # A rectangle is defined by its top-left corner and width and height.
    #
    # I'm assuming integer pixel coordinates where (0, 0) is the top left
    # corner of the screen, with down and right being the positive
    # directions.
    top_left: Point
    size: RectSize

    @property
    def bot_right(self):
        return Point(self.top_left.x + self.size.width - 1,
                     self.top_left.y + self.size.height - 1)


def rect_point_distance(rect: Rectangle, point: Point) -> float:
    """Gives L-infinity distance between point and the nearest part of rect.

    (I'm using L-infinity so the effective clickable area will be rectangular.)
    """
    if rect.top_left.x <= point.x <= rect.bot_right.x:
        x_distance = 0
    else:
        x_distance = min(abs(rect.top_left.x - point.x),
                         abs(rect.bot_right.x - point.x))
    if rect.top_left.y <= point.y <= rect.bot_right.y:
        y_distance = 0
    else:
        y_distance = min(abs(rect.top_left.y - point.y),
                         abs(rect.bot_right.y - point.y))
    return max(x_distance, y_distance)


# I don't know how you store the action associated with clicking a button, but
# it doesn't matter what it is. Probably a callback.
LinkValue = TypeVar("LinkValue")


def get_clicked_button(
        links_by_location: Mapping[Rectangle, LinkValue],
        extra_clickable_radius: int,
        click_pos: Point,
) -> Optional[LinkValue]:
    """Decides which button the user clicked on, if any.

    Buttons can include links or any other clickable element that's part of the
    ebook content. Not other Libby UI stuff like page-turns.

    Args:
      links_by_location: Map from rectangular button coordinates to effect of
        link. Note that multiple rectangles may map to the same effect, e.g.
        if a link is split up over a line break.
      extra_clickable_radius: Max distance a user can click outside of a link
        that still counts as clicking on the link. In pixels.
      click_pos: Where the user clicked. In the same pixel coordinate system as
        the links_by_location rects.

    Returns:
      One LinkValue representing the button that was clicked, or None if the
      click was not near any button.
    """
    nearby = [rect for rect in links_by_location
              if rect_point_distance(rect, click_pos) <= extra_clickable_radius]
    if not nearby:
        return None
    return links_by_location[
        min(nearby, key=lambda r: rect_point_distance(r, click_pos))]




#### Some test cases



# Basic stuff. Clicking the corner of a rectangle works, even with the "wiggle
# room" turned to 0.
assert get_clicked_button(
    {Rectangle(Point(10, 100), RectSize(20, 40)): "Correct",
     Rectangle(Point(2000, 200), RectSize(20, 40)): "Wrong"},
    0,
    Point(10, 100)) == "Correct"

# Test clicking far away from any button.
assert get_clicked_button(
    {Rectangle(Point(10, 100), RectSize(20, 40)): "Correct",
     Rectangle(Point(2000, 200), RectSize(20, 40)): "Wrong"},
    5,
    Point(1000, 120)) == None


nearby_dudes = {
    Rectangle(Point(10, 100), RectSize(10, 6000)): "Alice",
    Rectangle(Point(30, 100), RectSize(10, 7000)): "Bob"}

for dist in range(4):
    assert get_clicked_button(nearby_dudes, 4, Point(20 + dist, 150)) == "Alice"
assert get_clicked_button(nearby_dudes, 4, Point(25, 150)) == None
for dist in range(6, 10):
    assert get_clicked_button(nearby_dudes, 4, Point(20 + dist, 150)) == "Bob"

# Like the previous test but with the "wiggle room" cranked up too high. The
# user can still click on both buttons (although they might have trouble
# turning the page.)
for dist in range(4):
    assert get_clicked_button(nearby_dudes, 1000, Point(20 + dist, 150)) == "Alice"
for dist in range(6, 10):
    assert get_clicked_button(nearby_dudes, 1000, Point(20 + dist, 150)) == "Bob"
