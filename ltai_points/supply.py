import yaml


def get_supply_info(settings):
    # we read a yaml file defined in settings with the allocs details
    filename = settings['supply_filename']
    with open(filename, 'r') as f:
        supply_info = yaml.safe_load(f)
        pools = supply_info['pools']
        for pool in pools:
            pool['distributed'] = 0
        max_supply = supply_info['max_supply']
        allocations = supply_info['allocations']
        for alloc in allocations:
            alloc['distributed'] = 0
        return pools, max_supply, allocations

