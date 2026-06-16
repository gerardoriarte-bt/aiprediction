"""
Simulation environment routes: env-status, close-env.
"""

import traceback
from flask import request, jsonify

from .. import simulation_bp
from ...services.simulation_manager import SimulationManager, SimulationStatus
from ...services.simulation_runner import SimulationRunner
from ...utils.logger import get_logger
from ...utils.locale import t

logger = get_logger('mirofish.api.simulation')


@simulation_bp.route('/env-status', methods=['POST'])
def get_env_status():
    """
    获取模拟环境状态

    检查模拟环境是否存活（可以接收Interview命令）

    请求（JSON）：
        {
            "simulation_id": "sim_xxxx"  // 必填，模拟ID
        }

    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "env_alive": true,
                "twitter_available": true,
                "reddit_available": true,
                "message": "环境正在运行，可以接收Interview命令"
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')

        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        env_alive = SimulationRunner.check_env_alive(simulation_id)

        # 获取更详细的状态信息
        env_status = SimulationRunner.get_env_status_detail(simulation_id)

        if env_alive:
            message = t('api.envRunning')
        else:
            message = t('api.envNotRunningShort')

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "env_alive": env_alive,
                "twitter_available": env_status.get("twitter_available", False),
                "reddit_available": env_status.get("reddit_available", False),
                "message": message
            }
        })

    except Exception as e:
        logger.error(f"获取环境状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/close-env', methods=['POST'])
def close_simulation_env():
    """
    关闭模拟环境

    向模拟发送关闭环境命令，使其优雅退出等待命令模式。

    注意：这不同于 /stop 接口，/stop 会强制终止进程，
    而此接口会让模拟优雅地关闭环境并退出。

    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",  // 必填，模拟ID
            "timeout": 30                  // 可选，超时时间（秒），默认30
        }

    返回：
        {
            "success": true,
            "data": {
                "message": "环境关闭命令已发送",
                "result": {...},
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        timeout = data.get('timeout', 30)

        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        result = SimulationRunner.close_simulation_env(
            simulation_id=simulation_id,
            timeout=timeout
        )

        # 更新模拟状态
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
            state.status = SimulationStatus.COMPLETED
            manager._save_simulation_state(state)

        return jsonify({
            "success": result.get("success", False),
            "data": result
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except Exception as e:
        logger.error(f"关闭环境失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
