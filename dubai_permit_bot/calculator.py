def calculate_event_permit_cost(
    event_type,
    is_ticketed,
    venue_type=None,
    num_days=1,
    num_performers=0,
    is_urgent=False,
    is_amendment=False,
    has_exhibition=False,
    has_conference=False,
    has_award_ceremony=False
):
    """
    Calculate the total permit cost for an event based on various parameters.
    
    Parameters:
    - event_type: str - Type of event ('business', 'entertainment', 'sports_charity')
    - is_ticketed: bool - Whether the event is ticketed/registration-based
    - venue_type: str - Type of venue ('hotel', 'other') - required for entertainment events
    - num_days: int - Number of days for the event (default: 1)
    - num_performers: int - Number of performers (for entertainment events, default: 0)
    - is_urgent: bool - Whether urgent processing is needed (default: False)
    - is_amendment: bool - Whether this is an amendment to an application (default: False)
    - has_exhibition: bool - Whether the event includes an exhibition (for business events, default: False)
    - has_conference: bool - Whether the event includes a conference/forum/seminar/summit (for business events, default: False)
    - has_award_ceremony: bool - Whether the event includes an award ceremony (default: False)
    
    Returns:
    - dict: A dictionary containing the total cost and its breakdown
    """
    
    # Initialize cost components
    cost_components = {
        'base_fee': 0,
        'per_day_fee': 0,
        'performer_fee': 0,
        'e_permit_fee': 200,
        'knowledge_dirham': 10,
        'innovation_dirham': 10,
        'dtcm_management_fee': 500 if event_type == 'entertainment' else 0,
        'ded_fee': 50 if event_type == 'business' else 0,
        'urgent_fee': 500 if is_urgent else 0,
        'amendment_fee': 800 if is_amendment else 520 if (not is_ticketed and is_amendment) else 0
    }
    
    # Calculate base fee based on event type and ticketing status
    if event_type == 'business':
        if is_ticketed:
            if has_exhibition and has_conference:
                cost_components['base_fee'] = 1500
            elif has_exhibition:
                cost_components['base_fee'] = 1000
            elif has_conference:
                cost_components['base_fee'] = 1000
            else:
                cost_components['base_fee'] = 1000  # Default for ticketed business events
        else:  # Non-ticketed
            if has_exhibition and has_conference:
                cost_components['base_fee'] = 1500
            elif has_exhibition:
                cost_components['base_fee'] = 1000
            elif has_conference:
                cost_components['base_fee'] = 250
            else:
                cost_components['base_fee'] = 1000  # Default for non-ticketed business events
    
    elif event_type == 'entertainment':
        if is_ticketed:
            cost_components['base_fee'] = 800  # Event permit fee for ticketed
        else:  # Non-ticketed
            if venue_type == 'hotel':
                cost_components['base_fee'] = 800  # Per day
            else:
                cost_components['base_fee'] = 500  # Per day for other venues
            
            # Performer fees only apply to non-ticketed entertainment events
            if venue_type == 'hotel':
                cost_components['performer_fee'] = 750 * num_performers
            else:
                cost_components['performer_fee'] = 350 * num_performers
    
    elif event_type == 'sports_charity':
        cost_components['base_fee'] = 0  # No base fee, only additional fees apply
    
    # Calculate per day fee
    if event_type == 'entertainment' and not is_ticketed:
        if venue_type == 'hotel':
            cost_components['per_day_fee'] = 800 * num_days
        else:
            cost_components['per_day_fee'] = 500 * num_days
    else:
        # For ticketed entertainment and other event types, first day included in base fee
        cost_components['per_day_fee'] = 800 * (num_days - 1) if num_days > 1 else 0
    
    # Special cases for combined events
    if has_award_ceremony:
        if event_type == 'business':
            if is_ticketed:
                if has_conference and has_exhibition:
                    cost_components['base_fee'] = 3070 - cost_components['e_permit_fee'] - cost_components['knowledge_dirham'] - cost_components['innovation_dirham']
                elif has_conference:
                    cost_components['base_fee'] = 2570 - cost_components['e_permit_fee'] - cost_components['knowledge_dirham'] - cost_components['innovation_dirham']
                else:
                    cost_components['base_fee'] = 1520 - cost_components['e_permit_fee'] - cost_components['knowledge_dirham'] - cost_components['innovation_dirham']
            else:  # Non-ticketed
                if venue_type == 'hotel':
                    if has_conference and has_exhibition:
                        cost_components['base_fee'] = 3820 - cost_components['performer_fee'] - cost_components['e_permit_fee'] - cost_components['knowledge_dirham'] - cost_components['innovation_dirham']
                    elif has_conference:
                        cost_components['base_fee'] = 2790 - cost_components['performer_fee'] - cost_components['e_permit_fee'] - cost_components['knowledge_dirham'] - cost_components['innovation_dirham']
                    else:
                        cost_components['base_fee'] = 2270 - cost_components['performer_fee'] - cost_components['e_permit_fee'] - cost_components['knowledge_dirham'] - cost_components['innovation_dirham']
                else:  # Other venue
                    if has_conference and has_exhibition:
                        cost_components['base_fee'] = 2090  # This needs verification as the spreadsheet shows '?'
                    elif has_conference:
                        cost_components['base_fee'] = 2090 - cost_components['performer_fee'] - cost_components['e_permit_fee'] - cost_components['knowledge_dirham'] - cost_components['innovation_dirham']
                    else:
                        cost_components['base_fee'] = 1570 - cost_components['performer_fee'] - cost_components['e_permit_fee'] - cost_components['knowledge_dirham'] - cost_components['innovation_dirham']
    
    # Calculate total cost
    total_cost = sum(cost_components.values())
    
    # Prepare breakdown
    breakdown = {
        'total_cost': total_cost,
        'cost_breakdown': cost_components,
        'calculation_notes': []
    }
    
    # Add calculation notes
    if num_days > 1 and (event_type != 'entertainment' or is_ticketed):
        breakdown['calculation_notes'].append(f"Added {cost_components['per_day_fee']} AED for {num_days-1} additional day(s)")
    
    if num_performers > 0 and event_type == 'entertainment' and not is_ticketed:
        breakdown['calculation_notes'].append(f"Added {cost_components['performer_fee']} AED for {num_performers} performer(s) at {venue_type} venue")
    
    if is_urgent:
        breakdown['calculation_notes'].append("Added 500 AED urgent processing fee")
    
    if is_amendment:
        breakdown['calculation_notes'].append(f"Added {cost_components['amendment_fee']} AED amendment fee")
    
    return breakdown


# Example usage:
if __name__ == "__main__":
    # Example 1: Ticketed business event with conference and exhibition
    example1 = calculate_event_permit_cost(
        event_type='business',
        is_ticketed=True,
        has_conference=True,
        has_exhibition=True
    )
    print("Example 1 - Business Conference + Exhibition (Ticketed):")
    print(f"Total Cost: {example1['total_cost']} AED")
    print("Breakdown:", example1['cost_breakdown'])
    
    # Example 2: Non-ticketed entertainment event at hotel with 2 performers
    example2 = calculate_event_permit_cost(
        event_type='entertainment',
        is_ticketed=False,
        venue_type='hotel',
        num_performers=2
    )
    print("\nExample 2 - Entertainment Event at Hotel (Non-ticketed, 2 performers):")
    print(f"Total Cost: {example2['total_cost']} AED")
    print("Breakdown:", example2['cost_breakdown'])
    
    # Example 3: Award ceremony + conference at other venue (non-ticketed)
    example3 = calculate_event_permit_cost(
        event_type='business',
        is_ticketed=False,
        venue_type='other',
        has_award_ceremony=True,
        has_conference=True
    )
    print("\nExample 3 - Award Ceremony + Conference at Other Venue (Non-ticketed):")
    print(f"Total Cost: {example3['total_cost']} AED")
    print("Breakdown:", example3['cost_breakdown'])