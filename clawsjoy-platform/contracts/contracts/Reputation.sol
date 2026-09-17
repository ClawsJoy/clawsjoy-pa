// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Reputation
 * @notice Polygon 声誉合约 — 存储开发者地址到评分的映射
 * @dev 只有合约所有者（付费老板）才能评分
 */
contract Reputation {
    // ── 状态变量 ──

    /// @notice 合约所有者地址（付费老板）
    address public owner;

    /// @notice 开发者地址 → 评分（0–100）
    mapping(address => uint8) private _scores;

    // ── 事件 ──

    /// @notice 当开发者被评分时触发
    /// @param rator 评分者地址
    /// @param developer 被评分开发者地址
    /// @param score 评分
    event Rated(address indexed rator, address indexed developer, uint8 score);

    // ── 修饰器 ──

    modifier onlyOwner() {
        require(msg.sender == owner, "Reputation: only owner can rate");
        _;
    }

    // ── 构造函数 ──

    constructor() {
        owner = msg.sender;
    }

    // ── 核心函数 ──

    /**
     * @notice 为开发者评分（仅限合约所有者）
     * @param developer 开发者地址
     * @param score 评分（0–100）
     */
    function rate(address developer, uint8 score) external onlyOwner {
        require(developer != address(0), "Reputation: invalid developer address");
        require(score <= 100, "Reputation: score must be 0-100");

        _scores[developer] = score;

        emit Rated(msg.sender, developer, score);
    }

    /**
     * @notice 查询开发者的声誉评分
     * @param developer 开发者地址
     * @return uint8 评分（0–100）
     */
    function getReputation(address developer) external view returns (uint8) {
        return _scores[developer];
    }
}
