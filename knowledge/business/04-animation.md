# Animation & Micro-interactions

A static website feels dead. A premium website feels alive. Use motion to guide attention and delight the user, but never to distract.

## Core Rules
1.  **Speed:** Animations should be fast. 200ms-300ms is the sweet spot. Anything over 500ms feels sluggish.
2.  **Easing:** Never use `linear` easing. Use `ease-out` for entering elements and `ease-in` for exiting.
3.  **Purpose:** Every animation must have a reason. (e.g., hover states indicate clickability, skeleton loaders indicate loading).

## Required Interactions
Every interactive element MUST have a state change:
- **Buttons:** Change background color, scale slightly (0.98), or lift (translateY -2px) on hover/active.
- **Links:** Underline appears/disappears or color shift.
- **Inputs:** distinct border color or shadow on focus.

## CSS Examples
```css
/* Smooth Hover Lift */
.card {
    transition: transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.2s ease;
}
.card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}

/* Button Press */
.btn:active {
    transform: scale(0.98);
}
```

## JavaScript Enhancements
- Use `IntersectionObserver` to fade in elements as they scroll into view.
- Don't overdo it. "Scroll jacking" is forbidden.
