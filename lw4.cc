#include <iostream>
#define FILE "data.text"

using namespace std;

namespace mapreduce {
template<typename MapTask,
		 typename ReduceTask,
		 typename Datasource=datasource::directory_iterator<MapTask>,
		 typename Combiner=null_combiner,
		 typename IntermediateStore=intermediates::local_disk<MapTask> >
class job;

} // namespace mapreduce

class map_task
{
  public:
	typedef std::string   key_type;
	typedef std::ifstream value_type;
	typedef std::string   intermediate_key_type;
	typedef unsigned      intermediate_value_type;

	map_task(job::map_task_runner &runner);
	void operator()(key_type const &key, value_type const &value);
};

class reduce_task
{
  public:
	typedef std::string  key_type;
	typedef size_t       value_type;

	reduce_task(job::reduce_task_runner &runner);

	template<typename It>
	void operator()(typename map_task::intermediate_key_type const &key, It it, It ite)
};
