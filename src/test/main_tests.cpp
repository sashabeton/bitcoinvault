// Copyright (c) 2014-2018 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <chainparams.h>
#include <validation.h>
#include <net.h>

#include <test/test_bitcoin.h>

#include <boost/signals2/signal.hpp>
#include <boost/test/unit_test.hpp>

BOOST_FIXTURE_TEST_SUITE(main_tests, TestingSetup)

static void TestBlockSubsidyHalvings(const Consensus::Params& consensusParams)
{
    int maxHalvings = 64;
    CAmount nInitialSubsidy = (50 * COIN) >> 4; // start from third (3.125), after expedited period

    CAmount nPreviousSubsidy = nInitialSubsidy * 2; // for height == 0
    BOOST_CHECK_EQUAL(nPreviousSubsidy, nInitialSubsidy * 2);
    for (int nHalvings = 4; nHalvings < maxHalvings; nHalvings++) {
        int nHeight = nHalvings * consensusParams.nSubsidyHalvingInterval;
        CAmount nSubsidy = GetBlockSubsidy(nHeight + BOOTSTRAP_PERIOD - BITCOIN_HEAD_START, consensusParams);
        BOOST_CHECK(nSubsidy <= nInitialSubsidy);
        BOOST_CHECK_EQUAL(nSubsidy, nPreviousSubsidy / 2);
        nPreviousSubsidy = nSubsidy;
    }
    BOOST_CHECK_EQUAL(GetBlockSubsidy(maxHalvings * consensusParams.nSubsidyHalvingInterval, consensusParams), 0);
}

/* removed (due to expedited):
static void TestBlockSubsidyHalvings(int nSubsidyHalvingInterval)
{
    Consensus::Params consensusParams;
    consensusParams.nSubsidyHalvingInterval = nSubsidyHalvingInterval;
    TestBlockSubsidyHalvings(consensusParams);
}
*/

BOOST_AUTO_TEST_CASE(block_subsidy_test)
{
    const auto chainParams = CreateChainParams(CBaseChainParams::MAIN);
    TestBlockSubsidyHalvings(chainParams->GetConsensus()); // As in main
    /* removed (due to expedited):
    TestBlockSubsidyHalvings(150); // As in regtest
    TestBlockSubsidyHalvings(1000); // Just another interval
    */
}

BOOST_AUTO_TEST_CASE(subsidy_limit_test)
{
    const auto chainParams = CreateChainParams(CBaseChainParams::MAIN);
    CAmount nSum = 0;
    for (int nHeight = 0; nHeight < 14000000; nHeight += 50) {
        CAmount nSubsidy = GetBlockSubsidy(nHeight, chainParams->GetConsensus());
        BOOST_CHECK(nSubsidy <= 175 * COIN);
        nSum += nSubsidy * 50;
        BOOST_CHECK(MoneyRange(nSum));
    }
    BOOST_CHECK_EQUAL(nSum, CAmount{2099999997690000});
}

BOOST_AUTO_TEST_CASE(subsidy_schedule)
{
    const auto chainParams = CreateChainParams(CBaseChainParams::MAIN);
    int nHeight = 0;
    CAmount nExpectedReward = 0;

    nHeight = 0;
    nExpectedReward = 175 * COIN;
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight = 100; // bootstrap sub-period 1
    nExpectedReward = 175 * COIN;
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 29850; // bootstrap sub-period 2
    nExpectedReward = 150 * COIN;
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 26600; // bootstrap sub-period 3
    nExpectedReward = 125 * COIN;
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 26600; // bootstrap sub-period 4
    nExpectedReward = 100 * COIN;
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 26600; // bootstrap sub-period 5
    nExpectedReward = 75 * COIN;
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 26600; // bootstrap sub-period 6
    nExpectedReward = 50 * COIN;
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 26600; // bootstrap sub-period 7
    nExpectedReward = 25 * COIN;
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 26600; // bootstrap sub-period 8
    nExpectedReward = (25 * COIN) >> 1; // 12.5
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 26600; // bootstrap sub-period 9
    nExpectedReward = (25 * COIN) >> 2; // 6.25
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 26600; // after bootstrap
    nExpectedReward = (25 * COIN) >> 3; // 3.125
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 26600; // after bootstrap
    nExpectedReward = (25 * COIN) >> 3; // 3.125
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);

    nHeight += 26600; // after bootstrap
    nExpectedReward = (25 * COIN) >> 3; // 3.125
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, chainParams->GetConsensus()), nExpectedReward);
}

static bool ReturnFalse() { return false; }
static bool ReturnTrue() { return true; }

BOOST_AUTO_TEST_CASE(test_combiner_all)
{
    boost::signals2::signal<bool (), CombinerAll> Test;
    BOOST_CHECK(Test());
    Test.connect(&ReturnFalse);
    BOOST_CHECK(!Test());
    Test.connect(&ReturnTrue);
    BOOST_CHECK(!Test());
    Test.disconnect(&ReturnFalse);
    BOOST_CHECK(Test());
    Test.disconnect(&ReturnTrue);
    BOOST_CHECK(Test());
}
BOOST_AUTO_TEST_SUITE_END()
