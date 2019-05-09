import weakref
from Foundation import NSObject, NSRect, NSMakeRect, NSZeroRect
from AppKit import NSView, NSViewController, NSPopover, NSMinXEdge, NSMaxXEdge, \
    NSMinYEdge, NSMaxYEdge, NSPopoverBehaviorApplicationDefined, NSPopoverBehaviorTransient, \
    NSPopoverBehaviorSemitransient

from vanilla.vanillaBase import VanillaBaseObject, _breakCycles, _addAutoLayoutRules
from vanilla.nsSubclasses import getNSSubclass

_edgeMap = {
    "left": NSMinXEdge,
    "right": NSMaxXEdge,
    "top": NSMinYEdge,
    "bottom": NSMaxYEdge
}

try:
    NSPopoverBehaviorApplicationDefined
except NameError:
    NSPopoverBehaviorApplicationDefined = 0
    NSPopoverBehaviorTransient = 1
    NSPopoverBehaviorSemitransient = 2

_behaviorMap = {
    "applicationDefined": NSPopoverBehaviorApplicationDefined,
    "transient": NSPopoverBehaviorTransient,
    "semitransient": NSPopoverBehaviorSemitransient
}


class VanillaPopoverContentView(NSView):

    def _getContentView(self):
        return self


class VanillaPopoverDelegate(NSObject):

    def popoverWillShow_(self, notification):
        self.vanillaWrapper()._alertBindings("will show")

    def popoverDidShow_(self, notification):
        self.vanillaWrapper()._alertBindings("did show")

    def popoverWillClose_(self, notification):
        self.vanillaWrapper()._alertBindings("will close")

    def popoverDidClose_(self, notification):
        self.vanillaWrapper()._alertBindings("did close")


class Popover(VanillaBaseObject):

    """
    A popover capable of containing controls.

    **size** Tuple of form *(width, height)* representing the size of the content
    in the popover.

    **size** The parent view that the popover should pop out from. This can be either
    a vanilla object or an instance of NSView or NSView subclass.

    **preferredEdge** The edge of the parent view that you want the popover
    to pop out from. These are the options:
    +------------+
    | *"left"*   |
    +------------+
    | *"right"*  |
    +------------+
    | *"top"*    |
    +------------+
    | *"bottom"* |
    +------------+

    **behavior** The desired behavior of the popover. These are the options:
    +------------------------+-----------------------------------------------------+
    | *"applicationDefined"* | Corresponds to NSPopoverBehaviorApplicationDefined. |
    +------------------------+-----------------------------------------------------+
    | *"transient"*          | Corresponds to NSPopoverBehaviorTransient.          |
    +------------------------+-----------------------------------------------------+
    | *"semitransient"*      | Corresponds to NSPopoverBehaviorSemitransient.      |
    +------------------------+-----------------------------------------------------+
    """

    nsPopoverClass = NSPopover
    contentViewClass = VanillaPopoverContentView
    contentViewControllerClass = NSViewController

    def __init__(self, size, parentView=None, preferredEdge="top", behavior="semitransient"):
        if isinstance(parentView, VanillaBaseObject):
            parentView = parentView._getContentView()
        self._parentView = parentView
        self._preferredEdge = preferredEdge
        # content view and controller
        self._nsObject = getNSSubclass(self.contentViewClass).alloc().initWithFrame_(((0, 0), size))
        self._contentViewController = self.contentViewControllerClass.alloc().init()
        self._contentViewController.setView_(self._nsObject)
        # popover
        cls = getNSSubclass(self.nsPopoverClass)
        self._popover = cls.alloc().init()
        self._popover.setContentViewController_(self._contentViewController)
        self._popover.setBehavior_(_behaviorMap[behavior])
        # delegate
        self._delegate = VanillaPopoverDelegate.alloc().init()
        self._delegate.vanillaWrapper = weakref.ref(self)
        self._popover.setDelegate_(self._delegate)
        self._bindings = {}
        self._autoLayoutViews = {}

    def __del__(self):
        self._breakCycles()

    def _breakCycles(self):
        super(Popover, self)._breakCycles()
        view = self._getContentView()
        if view is not None:
            _breakCycles(view)
        self._contentViewController = None
        self._popover = None
        self._parentView = None
        self._delegate = None

    def open(self, parentView=None, preferredEdge=None, relativeRect=None):
        """
        Open the popover. If desired, the **parentView** may be specified.
        If not, the values assigned during init will be used. Additionally,
        a rect of form (x, y, width, height) may be specified to indicate
        where the popover should pop out from. If not provided, the parent
        view's bounds will be used.
        """
        if isinstance(parentView, VanillaBaseObject):
            parentView = parentView._getContentView()
        if parentView is None:
            parentView = self._parentView
        if relativeRect is not None:
            if not isinstance(relativeRect, NSRect):
                x, y, w, h = relativeRect
                relativeRect = NSMakeRect(x, y, w, h)
        else:
            relativeRect = NSZeroRect
        if preferredEdge is None:
            preferredEdge = self._preferredEdge
        preferredEdge = _edgeMap[preferredEdge]
        self._popover.showRelativeToRect_ofView_preferredEdge_(relativeRect, parentView, preferredEdge)

    def close(self):
        """
        Close the popover.

        Once a popover has been closed it can not be re-opened.
        """
        self._popover.close()

    def resize(self, width, height):
        """
        Change the size of the popover to **width** and **height**.
        """
        self._popover.setContentSize_((width, height))

    def bind(self, event, callback):
        """
        Bind a callback to an event.

        **event** A string representing the desired event. The options are:

        +----------------+-----------------------------------------------+
        | *"will show"*  | Called immediately before the popover shows.  |
        +----------------+-----------------------------------------------+
        | *"did show"*   | Called immediately after the popover shows.   |
        +----------------+-----------------------------------------------+
        | *"will close"* | Called immediately before the popover closes. |
        +----------------+-----------------------------------------------+
        | *"did close"*  | Called immediately after the popover closes.  |
        +----------------+-----------------------------------------------+
        """
        if event not in self._bindings:
            self._bindings[event] = []
        self._bindings[event].append(callback)

    def unbind(self, event, callback):
        """
        Unbind a callback from an event.

        **event** A string representing the desired event.
        Refer to *bind* for the options.

        **callback** The callback that has been bound to the event.
        """
        self._bindings[event].remove(callback)

    def _alertBindings(self, key):
        if hasattr(self, "_bindings"):
            if key in self._bindings:
                for callback in self._bindings[key]:
                    # XXX why return? there could be more than one binding.
                    return callback(self)

    def addAutoPosSizeRules(self, rules, metrics=None):
        """
        Add auto layout rules for controls/view in this view.

        **rules** must by a list of rule definitions.
        Rule definitions may take two forms:

        * strings that follow the `Visual Format Language <https://developer.apple.com/library/archive/documentation/UserExperience/Conceptual/AutolayoutPG/VisualFormatLanguage.html#//apple_ref/doc/uid/TP40010853-CH27-SW1>`_.
        * dictionaries with the following key/value pairs:

        +---------------------------+-------------------------------------------------------------------------+
        | key                       | value                                                                   |
        +===========================+=========================================================================+
        | *"view1"*                 | The vanilla wrapped view for the left side of the rule.                 |
        +---------------------------+-------------------------------------------------------------------------+
        | *"attribute1"*            | The attribute of the view for the left side of the rule.                |
        |                           | See below for options.                                                  |
        +---------------------------+-------------------------------------------------------------------------+
        | *"relation"* (optional)   | The relationship between the left side of the rule                      |
        |                           | and the right side of the rule. See below for options.                  |
        |                           | The default value is `"=="`.                                            |
        +---------------------------+-------------------------------------------------------------------------+
        | *"view2"*                 | The vanilla wrapped view for the right side of the rule.                |
        +---------------------------+-------------------------------------------------------------------------+
        | *"attribute2"*            | The attribute of the view for the right side of the rule.               |
        |                           | See below for options.                                                  |
        +---------------------------+-------------------------------------------------------------------------+
        | *"multiplier"* (optional) | The constant multiplied with the attribute on the right side of         |
        |                           | the rule as part of getting the modified attribute.               |
        |                           | The default value is `1`.                                               |
        +---------------------------+-------------------------------------------------------------------------+
        | *"constant"* (optional)   | The constant added to the multiplied attribute value on the right       |
        |                           | side of the rule to yield the final modified attribute.           |
        |                           | The default value is `0`.                                               |
        +---------------------------+-------------------------------------------------------------------------+

        The `attribute1` and `attribute2` options are:

        +-------------------+--------------------------------+
        | value             | AppKit equivalent              |
        +===================+================================+
        | *"left"*          | NSLayoutAttributeLeft          |
        +-------------------+--------------------------------+
        | *"right"*         | NSLayoutAttributeRight         |
        +-------------------+--------------------------------+
        | *"top"*           | NSLayoutAttributeTop           |
        +-------------------+--------------------------------+
        | *"bottom"*        | NSLayoutAttributeBottom        |
        +-------------------+--------------------------------+
        | *"leading"*       | NSLayoutAttributeLeading       |
        +-------------------+--------------------------------+
        | *"trailing"*      | NSLayoutAttributeTrailing      |
        +-------------------+--------------------------------+
        | *"width"*         | NSLayoutAttributeWidth         |
        +-------------------+--------------------------------+
        | *"height"*        | NSLayoutAttributeHeight        |
        +-------------------+--------------------------------+
        | *"centerX"*       | NSLayoutAttributeCenterX       |
        +-------------------+--------------------------------+
        | *"centerY"*       | NSLayoutAttributeCenterY       |
        +-------------------+--------------------------------+
        | *"baseline"*      | NSLayoutAttributeBaseline      |
        +-------------------+--------------------------------+
        | *"lastBaseline"*  | NSLayoutAttributeLastBaseline  |
        +-------------------+--------------------------------+
        | *"firstBaseline"* | NSLayoutAttributeFirstBaseline |
        +-------------------+--------------------------------+

        Refer to the `NSLayoutAttribute documentation <https://developer.apple.com/documentation/uikit/nslayoutattribute>`_
        for the information about what each of these do.

        The `relation` options are:

        +--------+------------------------------------+
        | value  | AppKit equivalent                  |
        +========+====================================+
        | *"<="* | NSLayoutRelationLessThanOrEqual    |
        +--------+------------------------------------+
        | *"=="* | NSLayoutRelationEqual              |
        +--------+------------------------------------+
        | *">="* | NSLayoutRelationGreaterThanOrEqual |
        +--------+------------------------------------+        

        Refer to the `NSLayoutRelation documentation <https://developer.apple.com/documentation/uikit/nslayoutrelation?language=objc>`_
        for the information about what each of these do.

        **metrics** may be either **None** or a dict containing
        key value pairs representing metrics keywords used in the
        rules defined with strings.
        """
        _addAutoLayoutRules(self, rules, metrics)
