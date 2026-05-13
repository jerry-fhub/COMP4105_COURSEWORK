from __future__ import annotations

from src.env.grid_overlay import GridWorld
from src.env.models import ResourceStatus, Robot, RobotMode


def update_robot_mode(robot: Robot, world: GridWorld) -> RobotMode:
    if robot.failed:
        robot.mode = RobotMode.FAILED
    elif robot.carrying_resource is not None:
        robot.mode = RobotMode.CARRYING
    elif robot.assignment is not None:
        resource = world.resources[robot.assignment]
        if robot.position == resource.position and resource.status == ResourceStatus.ASSIGNED:
            robot.mode = RobotMode.WAIT_FOR_TEAM
        else:
            robot.mode = RobotMode.MOVE_TO_TASK
    elif world.frontier_cells():
        robot.mode = RobotMode.EXPLORE
    else:
        robot.mode = RobotMode.IDLE
    return robot.mode
