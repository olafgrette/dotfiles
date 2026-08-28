-- Directional monitor resolution that does not require pixel-adjacent monitors.
--
-- Hyprland's built-in l/r/u/d monitor selectors only match monitors whose edges
-- touch within ~2px. Fractional scaling rounds logical sizes, so a scaled laptop
-- panel beside an external display is routinely a few pixels off and the
-- direction resolves to nothing at all. This picks by geometry instead: among
-- the monitors on the requested side, prefer the ones that share rows (columns,
-- for u/d) with the source, then the nearest one.

local M = {}

-- Slop, in logical px. Also what keeps an exactly-touching perpendicular edge
-- from counting as shared rows/columns.
local EPS = 1

local AXES = {
    l = { pos = "x", size = "w", perp = "y", perp_size = "h", sign = -1 },
    r = { pos = "x", size = "w", perp = "y", perp_size = "h", sign = 1 },
    u = { pos = "y", size = "h", perp = "x", perp_size = "w", sign = -1 },
    d = { pos = "y", size = "h", perp = "x", perp_size = "w", sign = 1 },
}

local function center(box, pos, size)
    return box[pos] + box[size] / 2
end

-- Lexicographic compare of the rank tuples built in M.pick.
local function outranks(a, b)
    for i = 1, #a do
        if a[i] ~= b[i] then
            return a[i] < b[i]
        end
    end
    return false
end

--- Logical layout box for a monitor. Hyprland reports the pixel mode in
--- width/height but positions monitors in logical coordinates, so undo the
--- transform (90/270, flipped or not, swap the axes) and the scale.
function M.box(m)
    local w, h = m.width, m.height
    if (tonumber(m.transform) or 0) % 2 == 1 then
        w, h = h, w
    end
    local scale = (type(m.scale) == "number" and m.scale > 0) and m.scale or 1
    return { name = m.name, x = m.x, y = m.y, w = w / scale, h = h / scale }
end

--- Name of the box in direction `dir` from `from`, or nil. Pure over plain
--- boxes so it can be exercised without a running compositor.
function M.pick(boxes, from, dir)
    local ax = AXES[dir]
    if not ax or not from then
        return nil
    end

    local best, best_rank
    for _, b in ipairs(boxes) do
        local ahead = (center(b, ax.pos, ax.size) - center(from, ax.pos, ax.size)) * ax.sign
        if b.name ~= from.name and ahead > EPS then
            local overlap = math.min(from[ax.perp] + from[ax.perp_size], b[ax.perp] + b[ax.perp_size])
                - math.max(from[ax.perp], b[ax.perp])
            local sideways = math.abs(center(b, ax.perp, ax.perp_size) - center(from, ax.perp, ax.perp_size))
            -- Either it shares rows/columns with the source, or it is at least
            -- more that way than sideways. Without the second test a monitor
            -- beside the source whose centre happens to sit a few px lower
            -- would answer for "down".
            if overlap > EPS or ahead > sideways then
                local gap
                if ax.sign > 0 then
                    gap = b[ax.pos] - (from[ax.pos] + from[ax.size])
                else
                    gap = from[ax.pos] - (b[ax.pos] + b[ax.size])
                end
                local rank = {
                    overlap > EPS and 0 or 1, -- monitors sharing rows/columns first
                    math.max(gap, 0),         -- then the nearest along the axis
                    sideways,                 -- then the least sideways offset
                }
                if not best_rank or outranks(rank, best_rank) then
                    best, best_rank = b, rank
                end
            end
        end
    end
    return best and best.name or nil
end

--- Name of the monitor in `dir` from the focused one, or nil.
function M.resolve(dir)
    local from = hl.get_active_monitor()
    if not from then
        return nil
    end
    local boxes = {}
    for _, m in ipairs(hl.get_monitors()) do
        boxes[#boxes + 1] = M.box(m)
    end
    return M.pick(boxes, M.box(from), dir)
end

--- Bind callback dispatching `action(name)` against the monitor in `dir`.
--- Does nothing when there is no monitor that way, like the built-in selectors.
function M.to(dir, action)
    return function()
        local name = M.resolve(dir)
        if name then
            hl.dispatch(action(name))
        end
    end
end

--- Bind callback moving the active workspace to the monitor in `dir`.
function M.workspace_to(dir)
    return M.to(dir, function(name)
        return hl.dsp.workspace.move({ monitor = name })
    end)
end

return M
